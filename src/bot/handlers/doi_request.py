import datetime
from telegram import Update
from telegram.ext import ContextTypes
from django.utils import timezone
from src.bot.models import Request, ChatUser

async def handle_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    text = message.text.strip()
    # Проверяем метку назначения, если она используется
    if "[SciArticle Search]" in text:  
        # Парсим DOI из команды, ожидается второй токен
        parts = text.split()
        if len(parts) >= 2:
            doi = parts[1]
        else:
            return  # неправильный формат, игнорируем

        chat_id = message.chat_id
        # Попробуем определить пользователя, инициировавшего запрос (если инфо передана).
        requesting_user = None
        # Например, SciArticleBot мог добавить ID пользователя после DOI:
        # /request <doi> user:<123456>
        for part in parts:
            if part.startswith("user:"):
                user_id_str = part.split("user:")[1]
                try:
                    user_id = int(user_id_str)
                    requesting_user, _ = ChatUser.objects.get_or_create(user_id=user_id)
                except ValueError:
                    pass

        # Создаем запись запроса в БД
        new_request = Request.objects.create(
            doi=doi,
            chat_id=chat_id,
            created_at=timezone.now(),
            expires_at=timezone.now() + datetime.timedelta(days=3),
            status="pending",
            user=requesting_user  # может быть None
        )
        # Отправляем сообщение в чат, чтобы участники видели запрос
        await context.bot.send_message(
            chat_id=chat_id, 
            text=f"📄 *Запрос на статью* {doi}\n_Пожалуйста, пришлите PDF-файл этой статьи ответом на это сообщение_",
            parse_mode="Markdown",
            reply_to_message_id=message.message_id  # ответом на команду, чтобы связь была явной
        )