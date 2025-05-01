import logging
import re

from asgiref.sync import sync_to_async
from django.db import IntegrityError
from django.utils import timezone
from telegram import Update
from telegram.ext import ContextTypes

from bot.models import ChatUser, Request

logger = logging.getLogger(__name__)

DOI_PATTERN = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)
USER_ID_PATTERN = re.compile(r"user:(\d+)")

@sync_to_async(thread_sensitive=True)
def fetch_chat_user(user_id: int):
    try:
        return ChatUser.objects.get(telegram_id=user_id)
    except ChatUser.DoesNotExist:
        return None

@sync_to_async(thread_sensitive=True)
def get_or_create_chat_user_async(telegram_id: int, defaults: dict):
    return ChatUser.objects.get_or_create(telegram_id=telegram_id, defaults=defaults)

@sync_to_async(thread_sensitive=True)
def create_request_async(**kwargs):
    return Request.objects.create(**kwargs)

async def handle_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not context.args:
        await update.message.reply_text("Пожалуйста, укажите DOI: /request <DOI>")
        return
    doi = context.args[0]
    if not DOI_PATTERN.match(doi):
        await update.message.reply_text("Некорректный формат DOI")
        return
    if len(doi) > 256:
        await update.message.reply_text("DOI слишком длинный")
        return

    chat_user, _ = await get_or_create_chat_user_async(
        update.effective_user.id,
        defaults={
            "username": update.effective_user.username or f"user_{update.effective_user.id}",
            "full_name": update.effective_user.full_name or "",
            "is_in_bot": True,
        },
    )

    try:
        new_request = await create_request_async(
        doi=doi,
        status="pending",
        chat_id=update.effective_chat.id,
        request_message_id=update.message.message_id,
        user=chat_user,
        created_at=timezone.now()
    )
    except IntegrityError as e:
        logger.exception("IntegrityError occurred while creating a new request: %s", e)
        await update.message.reply_text(
            "❌ Извините, запрос с таким DOI уже существует. Пожалуйста, введите другой DOI."
        )
        return

    await update.message.reply_text(
        f"✅ Запрос {doi} принят, жду PDF…",
        reply_to_message_id=update.message.message_id
    )
