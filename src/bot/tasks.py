import logging

from celery import shared_task
from django.conf import settings
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)

@shared_task
def edit_pdf_message(chat_id, message_id, file_id):
    """Celery task to edit message with PDF verification buttons.

    Args:
        chat_id: The chat ID where the message was sent
        message_id: The message ID to edit
        file_id: The file ID of the PDF document

    """
    try:
        # Initialize bot with token from settings
        bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)

        # Create inline keyboard with verification buttons
        keyboard = [
            [
                InlineKeyboardButton("Все верно", callback_data=f"pdf_verify_correct_{file_id}"),
                InlineKeyboardButton("PDF неверный", callback_data=f"pdf_verify_incorrect_{file_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Edit the message
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="Пожалуйста, проверьте PDF",
            reply_markup=reply_markup
        )

        logger.info(f"Successfully edited message {message_id} in chat {chat_id}")
    except Exception as e:
        logger.error(f"Error editing message: {str(e)}")
        # You might want to retry the task
        edit_pdf_message.retry(exc=e, countdown=5, max_retries=3)
