import logging
from django.utils import timezone
from telegram import Update, InputMediaDocument, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from asgiref.sync import sync_to_async

from bot.models import Request, ChatUser, PDFUpload, Config
from bot.tasks import schedule_notification_deletion

logger = logging.getLogger(__name__)

get_request = sync_to_async(Request.objects.get, thread_sensitive=True)
get_or_create_chat_user = sync_to_async(ChatUser.objects.get_or_create, thread_sensitive=True)
save_chat_user = sync_to_async(lambda u: u.save(), thread_sensitive=True)
create_pdf_upload = sync_to_async(PDFUpload.objects.create, thread_sensitive=True)
save_pdf_upload = sync_to_async(lambda p: p.save(), thread_sensitive=True)
save_request = sync_to_async(lambda r: r.save(), thread_sensitive=True)

async def handle_pdf_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(">> handle_pdf_upload got called; reply_to_msg=%s",
                bool(update.message.reply_to_message))

    reply_msg = update.message.reply_to_message
    if not reply_msg:
        logger.info(">> no reply_to_message — nothing to do")
        return
    orig_msg_id = reply_msg.message_id

    try:
        req = await get_request(request_message_id=orig_msg_id)
    except Request.DoesNotExist:
        return

    pdf_file = update.message.document
    file_id   = pdf_file.file_id
    file_name = pdf_file.file_name or "article.pdf"
    tg_file   = await context.bot.get_file(file_id)
    file_path = f"articles/{req.id}_{file_name}"
    await tg_file.download_to_drive(file_path)

    user_id  = update.message.from_user.id
    username = update.message.from_user.username or update.message.from_user.full_name
    chat_user, _ = await get_or_create_chat_user(
        telegram_id=user_id,
        defaults={"username": username}
    )
    chat_user.username     = username or chat_user.username
    chat_user.upload_count = (chat_user.upload_count or 0) + 1
    await save_chat_user(chat_user)

    pdf_upload = await create_pdf_upload(
        request=req,
        file=file_path,
        uploaded_at=timezone.now(),
        is_valid=None,
        validated_at=None,
        user=chat_user
    )
    pdf_upload.chat_message_id = orig_msg_id
    await save_pdf_upload(pdf_upload)

    req.status = "processing"
    await save_request(req)

    keyboard = InlineKeyboardMarkup([
        [
         InlineKeyboardButton("✅ Все верно", callback_data=f"vote_valid:{pdf_upload.id}"),
         InlineKeyboardButton("❌ PDF неверный", callback_data=f"vote_invalid:{pdf_upload.id}")
        ]
    ])
    new_caption = f"Пожалуйста, проверьте PDF {req.doi}"
    try:
        await context.bot.edit_message_media(
            chat_id=req.chat_id,
            message_id=orig_msg_id,
            media=InputMediaDocument(media=file_id, caption=new_caption)
        )
        await context.bot.edit_message_reply_markup(
            chat_id=req.chat_id,
            message_id=orig_msg_id,
            reply_markup=keyboard
        )
    except Exception:
        await context.bot.send_document(
            chat_id=req.chat_id,
            document=file_id,
            caption=new_caption,
            reply_markup=keyboard
        )

    if not chat_user.has_bot:
        notify_text = (
            f"@{chat_user.username}, помог {chat_user.upload_count} раз(а), "
            "поделившись исследованием! Зайдите в @SciArticleBot, чтобы получить награду."
        )
        notif = await context.bot.send_message(chat_id=req.chat_id, text=notify_text)
        schedule_notification_deletion(req.chat_id, notif.message_id, delay=3600)
    else:
        config = Config.get_instance()
        await context.bot.send_message(
            chat_id=chat_user.user_id,
            text=(
                f"Спасибо за загрузку PDF! Вы помогли {chat_user.upload_count} раз(а). "
                f"За {config.uploads_for_subscription} загрузок вы получаете подписку."
            )
        )
