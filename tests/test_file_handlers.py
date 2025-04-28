import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from telegram import Update, Chat, Message, User, Document, File
from telegram.ext import ContextTypes

from bot.handlers.file_handlers import handle_pdf_upload
from bot.models import Request, ChatUser, PDFUpload


@pytest.fixture
def telegram_update_with_pdf():
    """Create a mock Telegram Update object with a PDF document."""
    update = MagicMock(spec=Update)
    update.effective_chat = MagicMock(spec=Chat)
    update.effective_chat.id = 123456789
    
    # Create message
    update.message = MagicMock(spec=Message)
    update.message.chat_id = 123456789
    update.message.message_id = 987654321
    
    # Create reply_to_message
    update.message.reply_to_message = MagicMock(spec=Message)
    update.message.reply_to_message.message_id = 123123123
    
    # Create from_user
    update.message.from_user = MagicMock(spec=User)
    update.message.from_user.id = 123456789
    update.message.from_user.username = "test_user"
    update.message.from_user.full_name = "Test User"
    
    # Create document
    update.message.document = MagicMock(spec=Document)
    update.message.document.file_id = "test_file_id"
    update.message.document.file_name = "test_article.pdf"
    
    update.callback_query = None
    return update


@pytest.fixture
def telegram_context_for_file():
    """Create a mock Telegram Context object for file handling."""
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot = MagicMock()
    context.bot.send_message = AsyncMock()
    context.bot.edit_message_media = AsyncMock()
    context.bot.edit_message_reply_markup = AsyncMock()
    
    # Mock get_file
    file_mock = MagicMock(spec=File)
    file_mock.download_to_drive = AsyncMock()
    context.bot.get_file = AsyncMock(return_value=file_mock)
    
    return context


@pytest.mark.django_db
@pytest.mark.asyncio
@patch('bot.handlers.file_handlers.timezone')
@patch('bot.handlers.file_handlers.InlineKeyboardMarkup')
@patch('bot.handlers.file_handlers.InlineKeyboardButton')
@patch('bot.handlers.file_handlers.InputMediaDocument')
async def test_handle_pdf_upload(
    mock_input_media, mock_button, mock_keyboard, mock_timezone,
    telegram_update_with_pdf, telegram_context_for_file, request_obj
):
    """Test handling a PDF upload."""
    # Setup
    mock_now = MagicMock()
    mock_timezone.now.return_value = mock_now
    
    # Mock keyboard
    mock_keyboard_instance = MagicMock()
    mock_keyboard.return_value = mock_keyboard_instance
    
    # Mock InputMediaDocument
    mock_media_instance = MagicMock()
    mock_input_media.return_value = mock_media_instance
    
    # Set up request with the message_id that matches reply_to_message.message_id
    request_obj.request_message_id = telegram_update_with_pdf.message.reply_to_message.message_id
    request_obj.save()
    
    # Execute
    with patch('bot.handlers.file_handlers.Request.objects.get', return_value=request_obj):
        await handle_pdf_upload(telegram_update_with_pdf, telegram_context_for_file)
    
    # Verify
    # Check that a PDFUpload was created
    pdf_upload = PDFUpload.objects.filter(request=request_obj).first()
    assert pdf_upload is not None
    assert pdf_upload.file.endswith("test_article.pdf")
    assert pdf_upload.chat_message_id == telegram_update_with_pdf.message.reply_to_message.message_id
    
    # Check that the bot edited the message
    telegram_context_for_file.bot.edit_message_media.assert_called_once()
    telegram_context_for_file.bot.edit_message_reply_markup.assert_called_once()
    
    # Check that the request status was updated
    request_obj.refresh_from_db()
    assert request_obj.status == "processing"


@pytest.mark.asyncio
async def test_handle_pdf_upload_no_reply(telegram_update_with_pdf, telegram_context_for_file):
    """Test handling a PDF upload with no reply_to_message."""
    # Setup
    telegram_update_with_pdf.message.reply_to_message = None
    
    # Execute
    await handle_pdf_upload(telegram_update_with_pdf, telegram_context_for_file)
    
    # Verify
    # Check that no message was sent or edited (handler should return early)
    telegram_context_for_file.bot.edit_message_media.assert_not_called()
    telegram_context_for_file.bot.edit_message_reply_markup.assert_not_called()


@pytest.mark.asyncio
@patch('bot.handlers.file_handlers.Request.objects.get')
async def test_handle_pdf_upload_request_not_found(
    mock_get, telegram_update_with_pdf, telegram_context_for_file
):
    """Test handling a PDF upload when the request is not found."""
    # Setup
    mock_get.side_effect = Request.DoesNotExist
    
    # Execute
    await handle_pdf_upload(telegram_update_with_pdf, telegram_context_for_file)
    
    # Verify
    # Check that no message was sent or edited (handler should return early)
    telegram_context_for_file.bot.edit_message_media.assert_not_called()
    telegram_context_for_file.bot.edit_message_reply_markup.assert_not_called()