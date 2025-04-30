import datetime

from asgiref.sync import sync_to_async
from django.utils import timezone
from telegram import Update
from telegram.ext import ContextTypes

from bot.tasks import schedule_notification_deletion, schedule_pdf_deletion
from bot.models import ChatUser, PDFUpload, Validation, Request, Config

@sync_to_async(thread_sensitive=True)
def fetch_pdf_upload(pdf_id):
    return PDFUpload.objects.select_related("request", "user").get(id=pdf_id)

@sync_to_async(thread_sensitive=True)
def fetch_or_create_voter(telegram_id, defaults):
    return ChatUser.objects.get_or_create(telegram_id=telegram_id, defaults=defaults)

@sync_to_async(thread_sensitive=True)
def save_chat_user(user):
    user.save()
    return user

@sync_to_async(thread_sensitive=True)
def check_existing_validation(pdf_upload, user):
    return Validation.objects.filter(pdf_upload=pdf_upload, user=user).first()

@sync_to_async(thread_sensitive=True)
def create_validation(pdf_upload, user, vote, voted_at):
    return Validation.objects.create(
        pdf_upload=pdf_upload, user=user, vote=vote, voted_at=voted_at
    )

@sync_to_async(thread_sensitive=True)
def increment_validation_count(user):
    user.validation_count = (user.validation_count or 0) + 1
    user.save()
    return user.validation_count

@sync_to_async(thread_sensitive=True)
def fetch_config():
    return Config.objects.first()

@sync_to_async(thread_sensitive=True)
def count_votes(pdf_upload):
    qs = Validation.objects.filter(pdf_upload=pdf_upload)
    total = qs.count()
    correct = qs.filter(vote=True).count()
    return total, correct

@sync_to_async(thread_sensitive=True)
def finalize_pdf(pdf_upload, is_valid, validated_at):
    pdf_upload.is_valid = is_valid
    pdf_upload.validated_at = validated_at
    pdf_upload.save()
    return pdf_upload

@sync_to_async(thread_sensitive=True)
def update_request_status(req, status):
    req.status = status
    req.save()
    return req

@sync_to_async(thread_sensitive=True)
def create_retry_request(**kwargs):
    return Request.objects.create(**kwargs)

async def handle_vote_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data or ""

    try:
        action, pdf_id_str = data.split(":")
        pdf_id = int(pdf_id_str)
    except ValueError:
        return

    try:
        pdf_upload = await fetch_pdf_upload(pdf_id)
    except PDFUpload.DoesNotExist:
        return

    req = pdf_upload.request
    uploader = pdf_upload.user
    requester = req.user

    voter_id = query.from_user.id
    voter_name = query.from_user.username or query.from_user.full_name

    if requester and requester.telegram_id == voter_id:
        await context.bot.answer_callback_query(
            callback_query_id=query.id,
            text="Вы не можете голосовать по собственному запросу.",
            show_alert=True
        )
        return
    if uploader and uploader.telegram_id == voter_id:
        await context.bot.answer_callback_query(
            callback_query_id=query.id,
            text="Вы не можете голосовать за свой PDF.",
            show_alert=True
        )
        return

    voter, _ = await fetch_or_create_voter(
        telegram_id=voter_id,
        defaults={"username": voter_name}
    )
    voter.username = voter_name or voter.username
    await save_chat_user(voter)

    if await check_existing_validation(pdf_upload, voter):
        return

    vote_bool = (action == "vote_valid")
    await create_validation(pdf_upload, voter, vote_bool, timezone.now())
    new_count = await increment_validation_count(voter)

    config = await fetch_config()
    if config:
        thank_text = (
            f"Спасибо, что проверили PDF (DOI: {req.doi})! "
            f"Вы проверили {new_count} раз(а). "
            f"За {config.validations_for_subscription} проверок будет подписка."
        )
    else:
        thank_text = f"Спасибо, что проверили PDF (DOI: {req.doi})! Вы проверили {new_count} раз(а)."

    if not voter.has_bot:
        notif = await context.bot.send_message(
            chat_id=req.chat_id,
            text=f"@{voter.username}, вы проверили уже {new_count} раз(а)! "
                 "Подключитесь к @SciArticleBot для наград."
        )
        schedule_notification_deletion(req.chat_id, notif.message_id, delay=3600)
    else:
        await context.bot.send_message(chat_id=voter.telegram_id, text=thank_text)

    total_votes, correct_votes = await count_votes(pdf_upload)
    if total_votes >= 3:
        is_valid = correct_votes > (total_votes - correct_votes)
        await finalize_pdf(pdf_upload, is_valid, timezone.now())
        await context.bot.edit_message_reply_markup(
            chat_id=req.chat_id,
            message_id=pdf_upload.chat_message_id,
            reply_markup=None
        )
        await update_request_status(req, "completed")

        if is_valid:
            if requester and requester.has_bot:
                await context.bot.send_message(
                    chat_id=requester.telegram_id,
                    text=f"✅ PDF по запросу {req.doi} подтверждён! Спасибо."
                )
            else:
                await context.bot.send_message(
                    chat_id=req.chat_id,
                    text=f"✅ @{requester.username}, для {req.doi} найден корректный PDF!"
                )
        else:
            retry = await create_retry_request(
                doi=req.doi,
                chat_id=req.chat_id,
                created_at=timezone.now(),
                expires_at=timezone.now() + datetime.timedelta(days=3),
                status="pending",
                user=requester,
            )
            await context.bot.send_message(
                chat_id=req.chat_id,
                parse_mode="Markdown",
                text=(
                    f"📄 *Запрос на статью* {req.doi}\n"
                    "_Предыдущий PDF не подошёл, нужен новый._"
                )
            )

        schedule_pdf_deletion(pdf_upload.chat_message_id, req.chat_id, delay=3 * 24 * 3600)
