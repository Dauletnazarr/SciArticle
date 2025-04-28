import re

from asgiref.sync import sync_to_async
from django.utils import timezone
from telegram import Update
from telegram.ext import ContextTypes

from bot.models import ChatUser, Request

DOI_PATTERN = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)
USER_ID_PATTERN = re.compile(r"user:(\d+)")

@sync_to_async
def create_request_async(**kwargs):
    """Asynchronously creates a Request object."""
    return Request.objects.create(**kwargs)

@sync_to_async
def get_chat_user_async(user_id):
    """Asynchronously retrieves a ChatUser or returns None."""
    try:
        return ChatUser.objects.get(user_id=user_id)
    except ChatUser.DoesNotExist:
        return None
    except AttributeError:
         try:
             return ChatUser.objects.get(telegram_id=user_id)
         except ChatUser.DoesNotExist:
             return None

@sync_to_async
def get_or_create_chat_user_async(user_id, defaults=None):
    """Asynchronously gets or creates a ChatUser."""
    defaults = defaults or {}
    return ChatUser.objects.get_or_create(telegram_id=user_id, defaults=defaults)


async def handle_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles incoming messages looking for DOI requests."""
    if not update.message or not update.message.text:
        return

    message_text = update.message.text
    if not message_text.startswith("[SciArticle Search]"):
        return

    doi_match = DOI_PATTERN.search(message_text)
    if not doi_match:
        return

    doi = doi_match.group(0)
    user_id_match = USER_ID_PATTERN.search(message_text)
    chat_user = None
    requesting_user_id = update.message.from_user.id

    if user_id_match:
        target_user_id = int(user_id_match.group(1))
        chat_user = await get_chat_user_async(target_user_id)
        if not chat_user:
            pass
    else:
        chat_user, _ = await get_or_create_chat_user_async(
            requesting_user_id,
            defaults={
                'username': update.message.from_user.username or f"user_{requesting_user_id}",
                'full_name': update.message.from_user.full_name,
                'is_in_bot': True,
            }
        )

    new_request = await create_request_async(
        doi=doi,
        status="pending",
        chat_id=update.message.chat_id,
        request_message_id=update.message.message_id,
        user=chat_user,
        created_at=timezone.now()
    )

    await context.bot.send_message(
        chat_id=update.message.chat_id,
        text=f"Received request for DOI: {new_request.doi}. We will notify you when it's available.",
        reply_to_message_id=update.message.message_id
    )
