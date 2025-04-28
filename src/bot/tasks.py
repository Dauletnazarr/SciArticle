import logging

from celery import shared_task
from telegram import Bot

from bot.models import Config

logger = logging.getLogger(__name__)

@shared_task
def delete_message_task(chat_id, message_id):
    """Deletes a message after a delay, fetching config inside."""
    config = Config.objects.first()
    if not config or not config.bot_token:
        logger.error("Bot token not configured in DB for delete_message_task.")
        return
    bot = Bot(token=config.bot_token)
    try:
        bot.delete_message(chat_id=chat_id, message_id=message_id)
        logger.info(f"Deleted message {message_id} from chat {chat_id}")
    except Exception as e:
        logger.error(f"Failed to delete message {message_id} from chat {chat_id}: {e}")

@shared_task
def schedule_pdf_deletion(chat_id: int, message_id: int, delay: int):
    """Schedules the deletion of a PDF-related message."""
    delete_message_task.apply_async(args=[chat_id, message_id], countdown=delay)
    logger.info(
        f"Scheduled PDF message {message_id} in chat {chat_id} for deletion in {delay} seconds."
    )

@shared_task
def schedule_notification_deletion(chat_id: int, message_id: int, delay: int):
    """Schedules the deletion of a notification message."""
    delete_message_task.apply_async(args=[chat_id, message_id], countdown=delay)
    logger.info(
        f"Scheduled notification message {message_id} in chat {chat_id} for deletion in {delay} seconds."
    )
