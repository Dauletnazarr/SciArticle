from telegram import Update
from telegram.ext import ContextTypes

from bot.tasks import edit_pdf_message


async def handle_pdf_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle PDF file uploads and trigger verification process."""
    message = update.message

    # Check if the document is a PDF by MIME type or file extension
    document = message.document
    if document and (document.mime_type == 'application/pdf' or document.file_name.endswith('.pdf')):
        # Store message information in context.bot_data for processing
        message_id = message.message_id
        chat_id = update.effective_chat.id
        file_id = document.file_id

        # Send immediate response
        response_message = await message.reply_text("PDF получен, обрабатываю...")

        # Trigger async task to edit the message after a short delay
        edit_pdf_message.delay(
            chat_id=chat_id,
            message_id=response_message.message_id,
            file_id=file_id
        )
