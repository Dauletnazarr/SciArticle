from django.utils import timezone
from telegram import InputMediaDocument, Update
from telegram.ext import ContextTypes

from bot.models import ChatUser, PDFUpload, Request, Config
from bot.tasks import schedule_notification_deletion


async def handle_pdf_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    if not message.reply_to_message:
        return
    orig_msg_id = message.reply_to_message.message_id

    try:
        req = Request.objects.get(request_message_id=orig_msg_id)
    except Request.DoesNotExist:
        return

    pdf_file = message.document
    file_id = pdf_file.file_id
    file_name = pdf_file.file_name or "article.pdf"
    file_path = None

    file = await context.bot.get_file(file_id)
    file_path = f"articles/{req.id}_{file_name}"
    await file.download_to_drive(file_path)

    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.full_name
    chat_user, _ = ChatUser.objects.get_or_create(user_id=user_id, defaults={"username": username})
    chat_user.username = username or chat_user.username
    chat_user.upload_count = (chat_user.upload_count or 0) + 1
    chat_user.save()

    pdf_upload = PDFUpload.objects.create(
        request=req,
        file=file_path,
        uploaded_at=timezone.now(),
        is_valid=None,
        validated_at=None,
        user=chat_user
    )

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Все верно", callback_data=f"vote_valid:{pdf_upload.id}"),
         InlineKeyboardButton("❌ PDF неверный", callback_data=f"vote_invalid:{pdf_upload.id}")]
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
    pdf_upload.chat_message_id = orig_msg_id
    pdf_upload.save()

    req.status = "processing"
    req.save()

    if not chat_user.has_bot:
        notify_text = f"@{chat_user.username}, помог {chat_user.upload_count} раз(а), поделившись исследованием! Зайдите в @SciArticleBot, чтобы получить награду."
        notif_message = await context.bot.send_message(chat_id=req.chat_id, text=notify_text)
        schedule_notification_deletion(req.chat_id, notif_message.message_id, delay=3600)
    else:
        config = Config.get_instance()
        await context.bot.send_message(
            chat_id=chat_user.user_id,  # личный чат
            text=f"Спасибо за загрузку PDF! Вы помогли {chat_user.upload_count} раз(а). За {config.uploads_for_subscription} загрузок вы получаете подписку на бота."
        )
