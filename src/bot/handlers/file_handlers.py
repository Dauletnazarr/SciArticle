from django.utils import timezone
from telegram import InputMediaDocument, Update
from telegram.ext import ContextTypes

from bot.tasks import schedule_notification_deletion, config
from src.bot.models import Request, PDFUpload, ChatUser

async def handle_pdf_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    # Убеждаемся, что это ответ на сообщение запроса
    if not message.reply_to_message:
        return  # не привязано к запросу, игнорируем
    orig_msg_id = message.reply_to_message.message_id

    # Найти соответствующий запрос
    try:
        req = Request.objects.get(request_message_id=orig_msg_id)
    except Request.DoesNotExist:
        return  # запрос не найден (возможно, сообщение не нашлось в БД)

    # Получаем данные о файле
    pdf_file = message.document
    file_id = pdf_file.file_id
    file_name = pdf_file.file_name or "article.pdf"
    file_path = None

    # Сохраняем файл на сервер (скачиваем через Telegram API)
    file = await context.bot.get_file(file_id)
    # Предполагаем, что в настройках Django MEDIA_ROOT настроен, и PDFUpload.file хранит путь
    file_path = f"articles/{req.id}_{file_name}"
    await file.download_to_drive(file_path)  # скачиваем файл в указанный путь

    # Сохраняем информацию о пользователе, загрузившем PDF
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.full_name
    chat_user, _ = ChatUser.objects.get_or_create(user_id=user_id, defaults={"username": username})
    # Обновляем имя, на случай если поменялось
    chat_user.username = username or chat_user.username
    chat_user.upload_count = (chat_user.upload_count or 0) + 1
    chat_user.save()

    # Создаем запись PDFUpload
    pdf_upload = PDFUpload.objects.create(
        request=req,
        file=file_path,  # путь сохраненного PDF
        uploaded_at=timezone.now(),
        is_valid=None,
        validated_at=None,
        user=chat_user
    )

    # Готовим inline-кнопки для голосования
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Все верно", callback_data=f"vote_valid:{pdf_upload.id}"),
         InlineKeyboardButton("❌ PDF неверный", callback_data=f"vote_invalid:{pdf_upload.id}")]
    ])

    # Редактируем исходное сообщение запроса: прикрепляем PDF и меняем текст
    new_caption = f"Пожалуйста, проверьте PDF {req.doi}"
    try:
        # Заменяем текст и прикрепляем PDF как медиа (InputMediaDocument)
        await context.bot.edit_message_media(
            chat_id=req.chat_id,
            message_id=orig_msg_id,
            media=InputMediaDocument(media=file_id, caption=new_caption)
        )
        # Добавляем кнопки к отредактированному сообщению
        await context.bot.edit_message_reply_markup(
            chat_id=req.chat_id,
            message_id=orig_msg_id,
            reply_markup=keyboard
        )
    except Exception as e:
        # В случае ошибки (например, сообщение не найдено или старое) отправляем новое сообщение вместо редактирования
        await context.bot.send_document(
            chat_id=req.chat_id,
            document=file_id,
            caption=new_caption,
            reply_markup=keyboard
        )
    # Сохраняем ID сообщения с PDF (если мы отредактировали, это тот же orig_msg_id;
    # если отправили новое, нужно получить message_id нового сообщения)
    # Предположим, что мы смогли отредактировать:
    pdf_upload.chat_message_id = orig_msg_id
    pdf_upload.save()

    # Обновляем статус запроса – теперь на этапе проверки (можно статус "processing" или "pending_validation")
    req.status = "processing"
    req.save()

    # Отправляем уведомления об успехе загрузки (п.17)
    # Если пользователь не был в боте, уведомим его через чат
    if not chat_user.has_bot:
        # Уведомление в чат с упоминанием пользователя
        notify_text = f"@{chat_user.username}, помог {chat_user.upload_count} раз(а), поделившись исследованием! Зайдите в @SciArticleBot, чтобы получить награду."
        notif_message = await context.bot.send_message(chat_id=req.chat_id, text=notify_text)
        # Запланировать удаление этого уведомления через 1 час (Celery)
        schedule_notification_deletion(req.chat_id, notif_message.message_id, delay=3600)
    else:
        # Пользователь уже в боте – отправляем личное сообщение с благодарностью
        await context.bot.send_message(
            chat_id=chat_user.user_id,  # личный чат
            text=f"Спасибо за загрузку PDF! Вы помогли {chat_user.upload_count} раз(а). За {config.uploads_for_subscription} загрузок вы получаете подписку на бота."
        )
