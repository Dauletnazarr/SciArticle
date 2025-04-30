import re

from asgiref.sync import sync_to_async
from django.utils import timezone
from telegram import Update
from telegram.ext import ContextTypes

from bot.models import ChatUser, Request

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
    # if not msg or not msg.text or not msg.text.startswith("[SciArticle Search]"):
    #     return
    if not context.args:
        await update.message.reply_text("Пожалуйста, укажите DOI: /request <DOI>")
        return
    doi = context.args[0]

    # doi_match = DOI_PATTERN.search(msg.text)
    # if not doi_match:
    #     return
    # doi = doi_match.group(0)
    #
    # chat_user = None
    # user_id_match = USER_ID_PATTERN.search(msg.text)
    # if user_id_match:
    #     target_id = int(user_id_match.group(1))
    #     chat_user = await fetch_chat_user(target_id)
    #
    # if not chat_user:
    #     requester_id = msg.from_user.id
    #     username = msg.from_user.username or f"user_{requester_id}"
    #     full_name = msg.from_user.full_name or ""
    #     chat_user, _ = await get_or_create_chat_user_async(
    #         telegram_id=requester_id,
    #         defaults={
    #             "username": username,
    #             "full_name": full_name,
    #             "is_in_bot": True,
    #         }
    #     )
    #
    # new_request = await create_request_async(
    #     doi=doi,
    #     status="pending",
    #     chat_id=msg.chat_id,
    #     request_message_id=msg.message_id,
    #     user=chat_user,
    #     created_at=timezone.now(),
    # )
    #
    # await context.bot.send_message(
    #     chat_id=msg.chat_id,
    #     reply_to_message_id=msg.message_id,
    #     text=(
    #         f"Запрос на DOI `{new_request.doi}` принят.\n"
    #         "Как только PDF будет доступен — я вас уведомлю."
    #     ),
    #     parse_mode="Markdown"
    # )
    chat_user, _ = await get_or_create_chat_user_async(
        update.effective_user.id,
        defaults={
            "username": update.effective_user.username or f"user_{update.effective_user.id}",
            "full_name": update.effective_user.full_name or "",
            "is_in_bot": True,
        },
    )

    new_request = await create_request_async(
        doi=doi,
        status="pending",
        chat_id=update.effective_chat.id,
        request_message_id=update.message.message_id,
        user=chat_user,
        created_at=timezone.now()
    )

    await update.message.reply_text(
        f"✅ Запрос {doi} принят, жду PDF…",
        reply_to_message_id=update.message.message_id
    )