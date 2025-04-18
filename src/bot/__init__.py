from django.conf import settings
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from bot.hendlers.callback_handlers import handle_pdf_verification
from bot.hendlers.file_handlers import handle_pdf_file


def setup_bot():
    """Set up the Telegram bot with all handlers."""
    # Create the Application
    application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

    # Register handlers
    # ... (other command handlers)

    # File handlers
    application.add_handler(MessageHandler(filters.Document.ALL, handle_pdf_file))

    # Callback handlers
    application.add_handler(CallbackQueryHandler(handle_pdf_verification, pattern=r"^pdf_verify_"))

    return application

# Initialize the bot when the app is loaded
bot_application = setup_bot()
