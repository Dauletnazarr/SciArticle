import logging

import requests
from celery import shared_task
from django.db import IntegrityError
from telegram import Bot

from bot.models import Config

logger = logging.getLogger(__name__)

import os

from django.utils import timezone
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaDocument

from bot.models import ChatUser, PDFUpload, Request, Validation

TELEGRAM_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
SEND_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
bot = Bot(token=TELEGRAM_TOKEN)

def _send_sync(chat_id: int, text: str, reply_to: int = None):
    payload = {'chat_id': chat_id, 'text': text}
    if reply_to is not None:
        payload['reply_to_message_id'] = reply_to
    requests.post(SEND_URL, json=payload, timeout=5)


@shared_task
def create_request_task(doi: str, chat_id: int, message_id: int, user_id: int, username: str):
    chat_user, _ = ChatUser.objects.get_or_create(
        telegram_id=user_id,
        defaults={'username': username, 'is_in_bot': True}
    )
    try:
        req = Request.objects.create(
            doi=doi,
            chat_id=chat_id,
            request_message_id=message_id,
            status="pending",
            user=chat_user,
        )
        _send_sync(chat_id, f"✅ Принял запрос на DOI {doi}", reply_to=message_id)

    except IntegrityError:
        req = Request.objects.get(doi=doi)
        _send_sync(chat_id,
                   f"❗ Запрос на DOI {doi} уже существует (статус: {req.status}).",
                   reply_to=message_id)
    return req.id


@shared_task
def handle_pdf_upload_task(
    orig_msg_id: int, req_id: int,
    file_id: str, file_name: str,
    uploader_id: int, uploader_username: str
):
    req = Request.objects.get(pk=req_id)
    chat_user, _ = ChatUser.objects.get_or_create(
        telegram_id=uploader_id,
        defaults={'username': uploader_username}
    )
    pdf = PDFUpload.objects.create(
        request=req,
        file=f"articles/{req.id}_{file_name}",
        uploaded_at=timezone.now(),
        user=chat_user
    )
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Все верно", callback_data=f"vote_valid:{pdf.id}"),
            InlineKeyboardButton("❌ PDF неверный", callback_data=f"vote_invalid:{pdf.id}"),
        ]
    ])
    bot.edit_message_media(
        chat_id=req.chat_id,
        message_id=orig_msg_id,
        media=InputMediaDocument(media=file_id, caption=f"Проверьте PDF {req.doi}")
    )
    bot.edit_message_reply_markup(
        chat_id=req.chat_id, message_id=orig_msg_id, reply_markup=keyboard
    )
    return pdf.id


@shared_task
def handle_vote_callback_task(callback_data: str, voter_id: int, voter_username: str):
    action, pdf_id_str = callback_data.split(":")
    pdf_id = int(pdf_id_str)
    pdf = PDFUpload.objects.select_related('request','user').get(id=pdf_id)
    req = pdf.request

    if req.user and req.user.telegram_id == voter_id:
        bot.answer_callback_query(callback_query_id=None, text="Вы не можете голосовать по своему запросу.", show_alert=True)
        return
    if pdf.user.telegram_id == voter_id:
        bot.answer_callback_query(callback_query_id=None, text="Вы не можете голосовать за свой PDF.", show_alert=True)
        return

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
    if votes.count() >= 3:
        correct = votes.filter(vote=True).count()
        pdf.is_valid = correct > (votes.count() - correct)
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
