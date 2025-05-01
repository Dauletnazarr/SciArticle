import logging
from datetime import timedelta

import requests
from celery import shared_task
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from telegram import Bot

from bot.models import Config
from sciarticle.constants import MAX_FILE_SIZE

logger = logging.getLogger(__name__)

import os

from django.utils import timezone

from bot.models import ChatUser, PDFUpload, Request, Validation

TELEGRAM_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
SEND_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
bot = Bot(token=TELEGRAM_TOKEN)
logger = logging.getLogger(__name__)

def _send_sync(chat_id: int, text: str, reply_to: int = None):
    payload = {'chat_id': chat_id, 'text': text}
    if reply_to is not None:
        payload['reply_to_message_id'] = reply_to
    requests.post(SEND_URL, json=payload, timeout=5)

@shared_task(bind=True)
def create_request_task(self, doi, chat_id, message_id, user_id, username):
    try:
        logger.info("Create Request Task Started:")
        logger.info(f"DOI: {doi}")
        logger.info(f"Chat ID: {chat_id}")
        logger.info(f"Message ID: {message_id}")
        logger.info(f"User ID: {user_id}")
        logger.info(f"Username: {username}")

        user, created = ChatUser.objects.get_or_create(
            telegram_id=user_id, defaults={"username": username}
        )
        logger.info(f"User {'created' if created else 'found'}: {user.id}")

        try:
            existing_request = Request.objects.get(doi=doi)
            logger.warning(f"Request for DOI {doi} already exists. ID: {existing_request.id}")
            _send_sync(chat_id,
                       f"❗ Запрос на DOI {doi} уже существует (статус: {existing_request.status}).",
                       reply_to=message_id)
            if existing_request.user != user:
                logger.error(f"DOI {doi} already requested by another user")
                return None

            return existing_request.id
        except Request.DoesNotExist:
            request = Request.objects.create(
                doi=doi, chat_id=chat_id, request_message_id=message_id, user=user, status="PENDING"
            )
            _send_sync(chat_id, f"✅ Принял запрос на DOI {doi}", reply_to=message_id)
            logger.info(f"New request created: ID {request.id}, Message ID {message_id}")
            return request.id

    except Exception as e:
        logger.error(f"Unexpected error in create_request_task: {e}", exc_info=True)
        raise

@shared_task(bind=True, max_retries=3)
def handle_pdf_upload_task(
    self, request_message_id, file_id, file_name, user_id, uploader_username
):
    try:
        logger.info("PDF Upload Task Started:")
        logger.info(f"Request Message ID: {request_message_id}")
        logger.info(f"File ID: {file_id}")
        logger.info(f"File Name: {file_name}")
        logger.info(f"User ID: {user_id}")
        logger.info(f"Uploader Username: {uploader_username}")

        try:
            req = Request.objects.get(request_message_id=request_message_id)
            logger.info(f"Found request with matching message ID: {req.id}")
        except Request.DoesNotExist:
            recent_requests = Request.objects.filter(
                user__telegram_id=user_id, created_at__gte=timezone.now() - timedelta(hours=1)
            ).order_by("-created_at")

            logger.info(f"Total recent requests found: {recent_requests.count()}")

            if not recent_requests.exists():
                logger.error(f"No recent requests found for user {user_id}")
                return None

            matched_by_doi = False
            if "10." in file_name:
                possible_doi = file_name.split("10.")[1].split(".pdf")[0]
                possible_doi = f"10.{possible_doi}"

                for request in recent_requests:
                    if possible_doi in request.doi:
                        req = request
                        matched_by_doi = True
                        logger.info(f"Matched request by DOI in filename: {req.id}, DOI: {req.doi}")
                        break

            if not matched_by_doi:
                req = recent_requests.first()
                logger.warning(f"No DOI match found. Using most recent request: {req.id}")

        try:
            chat_user, created = ChatUser.objects.get_or_create(
                telegram_id=user_id, defaults={"username": uploader_username, "is_in_bot": True}
            )
        except Exception as user_create_error:
            logger.error(f"Error creating/retrieving user: {user_create_error}")
            return None

        try:
            get_file_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile"
            get_file_response = requests.get(get_file_url, params={"file_id": file_id}, timeout=30)
            get_file_response.raise_for_status()
            file_path = get_file_response.json()["result"]["file_path"]
            file_content = requests.get(
                f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}", timeout=30
            ).content

            if len(file_content) > MAX_FILE_SIZE:
                raise ValueError("File too large")
        except Exception as download_error:
            logger.error(f"File download error: {download_error}")
            return None

        try:
            django_path = default_storage.save(
                f"articles/{req.id}_{timezone.now().isoformat()}_{file_name}",
                ContentFile(file_content),
            )
        except Exception as storage_error:
            logger.error(f"File storage error: {storage_error}")
            return None

        try:
            pdf = PDFUpload.objects.create(
                request=req,
                file=django_path,
                uploaded_at=timezone.now(),
                user=chat_user,
                chat_message_id=req.request_message_id,
            )
        except Exception as pdf_create_error:
            logger.error(f"PDF upload record creation error: {pdf_create_error}")
            default_storage.delete(django_path)
            return None

        try:
            keyboard = {
                "inline_keyboard": [
                    [
                        {"text": "✅ Все верно", "callback_data": f"vote_valid:{pdf.id}"},
                        {"text": "❌ PDF неверный", "callback_data": f"vote_invalid:{pdf.id}"},
                    ]
                ]
            }
            send_document_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
            send_document_data = {
                "chat_id": req.chat_id,
                "document": file_id,
                "caption": f"Проверьте PDF {req.doi}",
                "reply_markup": keyboard,
            }
            response = requests.post(send_document_url, json=send_document_data, timeout=30)
            if not response.ok:
                logger.error(f"Telegram API error: {response.text}")
            else:
                new_message_id = response.json()["result"]["message_id"]
                pdf.chat_message_id = new_message_id
                pdf.save()
        except Exception as telegram_error:
            logger.error(f"Telegram message update error: {telegram_error}")

        return pdf.id

    except Exception as unexpected_error:
        logger.error(f"Unexpected error in PDF upload task: {unexpected_error}")
        return None


@shared_task
def handle_vote_callback_task(
    callback_query_id: str, callback_data: str, voter_id: int, voter_username: str
):
    action, pdf_id_str = callback_data.split(":")
    pdf_id = int(pdf_id_str)
    pdf = PDFUpload.objects.select_related('request','user').get(id=pdf_id)
    req = pdf.request
    if req.user and req.user.telegram_id == voter_id:
        return {"blocked": True, "message": "Вы не можете голосовать по своему запросу."}

    if pdf.user.telegram_id == voter_id:
        return {"blocked": True, "message": "Вы не можете голосовать за свой PDF."}

    voter, _ = ChatUser.objects.get_or_create(
        telegram_id=voter_id,
        defaults={'username': voter_username}
    )
    vote_val = (action == "vote_valid")
    Validation.objects.create(
        pdf_upload=pdf,
        user=voter,
        vote=vote_val,
        voted_at=timezone.now()
    )

    votes = Validation.objects.filter(pdf_upload=pdf)
    total_votes = votes.count()
    if total_votes >= 3:
        correct = votes.filter(vote=True).count()
        pdf.is_valid = correct > (total_votes - correct)
        pdf.validated_at = timezone.now()
        pdf.save()
    return pdf.id


@shared_task
def delete_message_task(chat_id, message_id):
    """Deletes a message after a delay, fetching config inside."""
    config = Config.objects.first()
    if not config or not config.bot_token:
        logger.error("Bot token not configured in DB for delete_message_task.")
        return
    bot = Bot(token=config.bot_token)
    try:
        bot.delete_message(chat_id=chat_id, message_id=message_id)
        logger.info(f"Deleted message {message_id} from chat {chat_id}")
    except Exception as e:
        logger.error(f"Failed to delete message {message_id} from chat {chat_id}: {e}")

@shared_task
def schedule_pdf_deletion(chat_id: int, message_id: int, delay: int):
    """Schedules the deletion of a PDF-related message."""
    delete_message_task.apply_async(args=[chat_id, message_id], countdown=delay)
    logger.info(
        f"Scheduled PDF message {message_id} in chat {chat_id} for deletion in {delay} seconds."
    )

@shared_task
def schedule_notification_deletion(chat_id: int, message_id: int, delay: int):
    """Schedules the deletion of a notification message."""
    delete_message_task.apply_async(args=[chat_id, message_id], countdown=delay)
    logger.info(
        f"Scheduled notification message {message_id} in chat {chat_id} for deletion in {delay} seconds."
    )
