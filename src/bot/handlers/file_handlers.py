import logging
import os

from bot.tasks import handle_pdf_upload_task
from sciarticle.constants import MAX_FILE_SIZE

logger = logging.getLogger(__name__)

async def handle_pdf_upload(update, context):
    try:
        msg = update.message
        if msg.document.file_size > MAX_FILE_SIZE:
            await context.bot.send_message(
                chat_id=msg.chat_id, text="❌ Файл слишком большой. Максимальный размер 10 МБ."
            )
            return

        if not msg.document.file_name.lower().endswith(".pdf"):
            await context.bot.send_message(
                chat_id=msg.chat_id, text="❌ Пожалуйста, загрузите только PDF файл."
            )
            return

        if not msg.reply_to_message:
            logger.warning("PDF upload without reply message")
            return

        if not msg.document:
            logger.error("No document in the message")
            return

        os.makedirs('/tmp/sciarticle', exist_ok=True)

        f = await context.bot.get_file(msg.document.file_id)
        tmp_path = f"/tmp/sciarticle/{msg.document.file_id}"

        try:
            await f.download_to_drive(tmp_path)
        except Exception as e:
            logger.error(f"Failed to download file: {e}")
            return

        req_msg_id = msg.reply_to_message.message_id

        handle_pdf_upload_task.delay(
            msg.reply_to_message.message_id,
            msg.document.file_id,
            msg.document.file_name or 'unnamed.pdf',
            msg.from_user.id,
            msg.from_user.username or msg.from_user.full_name
        )

        logger.info("Sent handle_pdf_upload_task to Celery for Request %d", req_msg_id)

    except Exception as e:
        logger.error(f"Unexpected error in handle_pdf_upload: {e}", exc_info=True)
