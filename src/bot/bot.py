import logging
import os
import sys

import django
from asgiref.sync import sync_to_async
from telegram import Update

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sciarticle.settings")
django.setup()

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from bot.handlers.callback_handlers import handle_vote_callback
from bot.handlers.file_handlers import handle_pdf_upload
from bot.models import ChatUser, Config, Subscription

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

get_or_create_user = sync_to_async(
    ChatUser.objects.get_or_create,
    thread_sensitive=True
)

get_user = sync_to_async(ChatUser.objects.get, thread_sensitive=True)
get_active_subs = sync_to_async(
    lambda user: list(
        Subscription.objects.filter(
            user=user, end_date__gt=django.utils.timezone.now()
        ).order_by('-end_date')
    ),
    thread_sensitive=True
)
get_config = sync_to_async(Config.get_instance, thread_sensitive=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler - registers user and sends welcome message."""
    user = update.effective_user

    chat_user, created = await get_or_create_user(
        telegram_id=user.id,
        defaults={
            'username': user.username or user.first_name,
            'is_in_bot': True
        }
    )

    if not chat_user.is_in_bot:
        chat_user.is_in_bot = True
        await sync_to_async(chat_user.save, thread_sensitive=True)()

    welcome_message = (
        f"Привет, {user.first_name}! Я SciArticleBot.\n\n"
        "Я помогаю находить научные статьи по DOI.\n\n"
        "Команды:\n"
        "/request <DOI> - запросить статью по DOI\n"
        "/stats - показать вашу статистику"
    )

    await update.message.reply_text(welcome_message)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the /stats command - shows user statistics."""
    user_id = update.effective_user.id

    try:
        user = await get_user(telegram_id=user_id)

        active_subs = await get_active_subs(user)

        sub_status = "Нет активных подписок"
        if active_subs:
            sub = active_subs[0]
            days_left = (sub.end_date - django.utils.timezone.now()).days
            sub_status = f"Активная подписка до {sub.end_date.strftime('%d.%m.%Y')} ({days_left} дней)"

        config = await get_config()

        uploads = user.upload_count
        validations = user.validation_count
        uploads_needed = config.uploads_for_subscription - (uploads % config.uploads_for_subscription)
        validations_needed = config.validations_for_subscription - (validations % config.validations_for_subscription)

        stats_text = (
            f"📊 Ваша статистика:\n\n"
            f"Загружено PDF: {uploads}\n"
            f"Проверено PDF: {validations}\n\n"
            f"Статус подписки: {sub_status}\n\n"
            f"До следующей подписки осталось:\n"
            f"- Загрузить еще {uploads_needed} PDF\n"
            f"- ИЛИ проверить еще {validations_needed} PDF"
        )

        await update.message.reply_text(stats_text)

    except ChatUser.DoesNotExist:
        await update.message.reply_text(
            "Вы еще не зарегистрированы. Используйте /start для начала работы."
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the /help command."""
    help_text = (
        "🔍 *SciArticleBot* - бот для поиска научных статей\n\n"
        "*Доступные команды:*\n"
        "/start - начать работу с ботом\n"
        "/stats - показать вашу статистику\n"
        "/help - показать эту справку\n\n"
        "*Как это работает:*\n"
        "1. Дождитесь, пока кто-то загрузит PDF\n"
        "2. Проверьте загруженный PDF голосованием\n"
        "3. Получайте подписку за загрузки и проверки"
    )

    await update.message.reply_text(help_text, parse_mode="Markdown")


def main():
    """Main function to start the bot."""
    if not TELEGRAM_TOKEN:
        logger.error("No TELEGRAM_BOT_TOKEN provided")
        return

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("help", help_command))

    application.add_handler(MessageHandler(
        filters.Document.PDF, handle_pdf_upload
    ))

    application.add_handler(CallbackQueryHandler(
        handle_vote_callback, pattern="^vote_"
    ))

    async def error_handler(update, context):
        logger.error(
            f"Update {update} caused error: {context.error}",
            exc_info=context.error
        )

    application.add_error_handler(error_handler)

    application.run_polling()

    logger.info("Bot started")


if __name__ == "__main__":
    main()
