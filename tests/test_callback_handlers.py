import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from telegram import Update, Chat, Message, User, CallbackQuery
from telegram.ext import ContextTypes

from bot.handlers.callback_handlers import handle_vote_callback
from bot.models import Request, ChatUser, PDFUpload, Validation


@pytest.fixture
def telegram_update_with_callback():
    """Create a mock Telegram Update object with a callback query."""
    update = MagicMock(spec=Update)
    update.effective_chat = MagicMock(spec=Chat)
    update.effective_chat.id = 123456789
    
    # Create callback_query
    update.callback_query = MagicMock(spec=CallbackQuery)
    update.callback_query.id = "callback_id_123"
    update.callback_query.data = "vote_valid:1"  # Default to valid vote for PDF ID 1
    update.callback_query.answer = AsyncMock()
    
    # Create from_user for callback_query
    update.callback_query.from_user = MagicMock(spec=User)
    update.callback_query.from_user.id = 987654321  # Different from uploader/requester
    update.callback_query.from_user.username = "voter_user"
    update.callback_query.from_user.full_name = "Voter User"
    
    update.message = None
    return update


@pytest.fixture
def telegram_context_for_callback():
    """Create a mock Telegram Context object for callback handling."""
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot = MagicMock()
    context.bot.send_message = AsyncMock()
    context.bot.edit_message_reply_markup = AsyncMock()
    context.bot.answer_callback_query = AsyncMock()
    return context


@pytest.mark.django_db
@pytest.mark.asyncio
@patch('bot.handlers.callback_handlers.timezone')
@patch('bot.handlers.callback_handlers.schedule_pdf_deletion')
async def test_handle_vote_callback_valid(
    mock_schedule_deletion, mock_timezone,
    telegram_update_with_callback, telegram_context_for_callback,
    pdf_upload, another_chat_user
):
    """Test handling a valid vote callback."""
    # Setup
    mock_now = MagicMock()
    mock_timezone.now.return_value = mock_now
    
    # Set the callback data to vote for the pdf_upload fixture
    telegram_update_with_callback.callback_query.data = f"vote_valid:{pdf_upload.id}"
    
    # Set the voter's telegram_id to match another_chat_user
    telegram_update_with_callback.callback_query.from_user.id = another_chat_user.telegram_id
    
    # Execute
    await handle_vote_callback(telegram_update_with_callback, telegram_context_for_callback)
    
    # Verify
    # Check that the callback was answered
    telegram_update_with_callback.callback_query.answer.assert_called_once()
    
    # Check that a Validation was created
    validation = Validation.objects.filter(pdf_upload=pdf_upload, user=another_chat_user).first()
    assert validation is not None
    assert validation.vote is True
    
    # Check that the user's validation_count was incremented
    another_chat_user.refresh_from_db()
    assert another_chat_user.validation_count == 1


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_handle_vote_callback_invalid_format(
    telegram_update_with_callback, telegram_context_for_callback
):
    """Test handling a callback with invalid format."""
    # Setup
    telegram_update_with_callback.callback_query.data = "invalid_format"
    
    # Execute
    await handle_vote_callback(telegram_update_with_callback, telegram_context_for_callback)
    
    # Verify
    # Check that the callback was answered
    telegram_update_with_callback.callback_query.answer.assert_called_once()
    
    # Check that no other actions were taken
    telegram_context_for_callback.bot.send_message.assert_not_called()
    telegram_context_for_callback.bot.edit_message_reply_markup.assert_not_called()


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_handle_vote_callback_pdf_not_found(
    telegram_update_with_callback, telegram_context_for_callback
):
    """Test handling a callback for a non-existent PDF."""
    # Setup
    telegram_update_with_callback.callback_query.data = "vote_valid:999999"  # Non-existent ID
    
    # Execute
    await handle_vote_callback(telegram_update_with_callback, telegram_context_for_callback)
    
    # Verify
    # Check that the callback was answered
    telegram_update_with_callback.callback_query.answer.assert_called_once()
    
    # Check that no other actions were taken
    telegram_context_for_callback.bot.send_message.assert_not_called()
    telegram_context_for_callback.bot.edit_message_reply_markup.assert_not_called()


@pytest.mark.django_db
@pytest.mark.asyncio
async def test_handle_vote_callback_uploader_voting(
    telegram_update_with_callback, telegram_context_for_callback,
    pdf_upload, chat_user
):
    """Test handling a vote from the uploader (should be blocked)."""
    # Setup
    telegram_update_with_callback.callback_query.data = f"vote_valid:{pdf_upload.id}"
    
    # Set the voter's telegram_id to match the uploader (chat_user)
    telegram_update_with_callback.callback_query.from_user.id = chat_user.telegram_id
    
    # Execute
    await handle_vote_callback(telegram_update_with_callback, telegram_context_for_callback)
    
    # Verify
    # Check that the callback was answered
    telegram_update_with_callback.callback_query.answer.assert_called_once()
    
    # Check that an error message was shown
    telegram_context_for_callback.bot.answer_callback_query.assert_called_once()
    args, kwargs = telegram_context_for_callback.bot.answer_callback_query.call_args
    assert kwargs['callback_query_id'] == telegram_update_with_callback.callback_query.id
    assert "не можете голосовать" in kwargs['text']
    assert kwargs['show_alert'] is True
    
    # Check that no Validation was created
    validation = Validation.objects.filter(pdf_upload=pdf_upload, user=chat_user).first()
    assert validation is None


@pytest.mark.django_db
@pytest.mark.asyncio
@patch('bot.handlers.callback_handlers.timezone')
@patch('bot.handlers.callback_handlers.schedule_pdf_deletion')
async def test_handle_vote_callback_multiple_votes(
    mock_schedule_deletion, mock_timezone,
    telegram_update_with_callback, telegram_context_for_callback,
    pdf_upload, another_chat_user
):
    """Test handling multiple votes that trigger validation completion."""
    # Setup
    mock_now = MagicMock()
    mock_timezone.now.return_value = mock_now
    
    # Create two more users for voting
    user2 = ChatUser.objects.create(telegram_id=111222333, username="user2")
    user3 = ChatUser.objects.create(telegram_id=444555666, username="user3")
    
    # Set the callback data to vote for the pdf_upload fixture
    telegram_update_with_callback.callback_query.data = f"vote_valid:{pdf_upload.id}"
    
    # First vote from another_chat_user
    telegram_update_with_callback.callback_query.from_user.id = another_chat_user.telegram_id
    await handle_vote_callback(telegram_update_with_callback, telegram_context_for_callback)
    
    # Second vote from user2
    telegram_update_with_callback.callback_query.from_user.id = user2.telegram_id
    await handle_vote_callback(telegram_update_with_callback, telegram_context_for_callback)
    
    # Third vote from user3 (this should trigger validation completion)
    telegram_update_with_callback.callback_query.from_user.id = user3.telegram_id
    await handle_vote_callback(telegram_update_with_callback, telegram_context_for_callback)
    
    # Verify
    # Check that the PDF was marked as valid
    pdf_upload.refresh_from_db()
    assert pdf_upload.is_valid is True
    assert pdf_upload.validated_at is not None
    
    # Check that the request was marked as completed
    pdf_upload.request.refresh_from_db()
    assert pdf_upload.request.status == "completed"
    
    # Check that the keyboard was removed
    telegram_context_for_callback.bot.edit_message_reply_markup.assert_called_with(
        chat_id=pdf_upload.request.chat_id,
        message_id=pdf_upload.chat_message_id,
        reply_markup=None
    )
    
    # Check that PDF deletion was scheduled
    mock_schedule_deletion.assert_called_once()