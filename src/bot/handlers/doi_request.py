import logging

from bot.tasks import create_request_task

logger = logging.getLogger(__name__)

async def handle_request(update, context):
    text = update.message.text or ""
    if not text.startswith("/request"):
     return

    parts = text.split(" ", 1)
    if len(parts) < 2 or not parts[1].strip():
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Error: Please provide a DOI after the /request command.",
        )
        return
    doi = parts[1].strip()
    user = update.effective_user

    create_request_task.delay(
         doi,
         update.effective_chat.id,
         update.message.message_id,
         user.id,
         user.username or user.full_name
     )
    logger.info("Sent create_request_task to Celery for DOI %s", doi)