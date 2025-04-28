import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from telegram import Update, Chat, Message, User, Document
from telegram.ext import ContextTypes

from bot.handlers.start import start_handler
from bot.handlers.help import help_handler
from bot.handlers.doi_request import handle_request
from bot.models import Request, ChatUser


@pytest.fixture
def telegram_update():
    """Create a mock Telegram Update object."""
    update = MagicMock(spec=Update)
    update.effective_chat = MagicMock(spec=Chat)
    update.effective_chat.id = 123456789
    update.message = MagicMock(spec=Message)
    update.message.chat_id = 123456789
    update.message.message_id = 987654321
    update.message.from_user = MagicMock(spec=User)
    update.message.from_user.id = 123456789
    update.message.from_user.username = "test_user"
    update.message.from_user.full_name = "Test User"
    update.message.text = "Test message"
    update.callback_query = None
    return update


@pytest.fixture
def telegram_context():
    """Create a mock Telegram Context object."""
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot = MagicMock()
    context.bot.send_message = AsyncMock()
    context.bot.edit_message_media = AsyncMock()
    context.bot.edit_message_reply_markup = AsyncMock()
    context.bot.get_file = AsyncMock()
    return context


@pytest.mark.asyncio
async def test_start_handler(telegram_update, telegram_context):
    """Test the start handler."""
    await start_handler(telegram_update, telegram_context)
    
    # Check that the bot sent a message
    telegram_context.bot.send_message.assert_called_once_with(
        chat_id=telegram_update.effective_chat.id,
        text='Приветственное сообщение',
    )


@pytest.mark.asyncio
async def test_help_handler(telegram_update, telegram_context):
    """Test the help handler."""
    await help_handler(telegram_update, telegram_context)
    
    # Check that the bot sent a message
    telegram_context.bot.send_message.assert_called_once_with(
        chat_id=telegram_update.effective_chat.id,
        text='help me!'
    )


@pytest.mark.django_db
@pytest.mark.asyncio
@patch('bot.handlers.doi_request.timezone')
async def test_handle_request_valid(mock_timezone, telegram_update, telegram_context):
    """Test handling a valid DOI request."""
    # Setup
    mock_now = MagicMock()
    mock_timezone.now.return_value = mock_now
    
    telegram_update.message.text = "[SciArticle Search] 10.1234/test.doi"
    
    # Execute
    await handle_request(telegram_update, telegram_context)
    
    # Verify
    # Check that a Request was created
    request = Request.objects.filter(doi="10.1234/test.doi").first()
    assert request is not None
    assert request.chat_id == telegram_update.message.chat_id
    assert request.status == "pending"
    
    # Check that the bot sent a message
    telegram_context.bot.send_message.assert_called_once()
    args, kwargs = telegram_context.bot.send_message.call_args
    assert kwargs['chat_id'] == telegram_update.message.chat_id
    assert "10.1234/test.doi" in kwargs['text']
    assert kwargs['reply_to_message_id'] == telegram_update.message.message_id


@pytest.mark.django_db
@pytest.mark.asyncio
@patch('bot.handlers.doi_request.timezone')
async def test_handle_request_with_user(mock_timezone, telegram_update, telegram_context, chat_user):
    """Test handling a DOI request with a user specified."""
    # Setup
    mock_now = MagicMock()
    mock_timezone.now.return_value = mock_now
    
    telegram_update.message.text = f"[SciArticle Search] 10.1234/test.doi user:{chat_user.telegram_id}"
    
    # Execute
    await handle_request(telegram_update, telegram_context)
    
    # Verify
    # Check that a Request was created with the correct user
    request = Request.objects.filter(doi="10.1234/test.doi").first()
    assert request is not None
    assert request.user == chat_user
    
    # Check that the bot sent a message
    telegram_context.bot.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_handle_request_invalid_format(telegram_update, telegram_context):
    """Test handling an invalid DOI request format."""
    # Setup
    telegram_update.message.text = "[SciArticle Search]"  # Missing DOI
    
    # Execute
    await handle_request(telegram_update, telegram_context)
    
    # Verify
    # Check that no message was sent (handler should return early)
    telegram_context.bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_handle_request_not_sciarticle(telegram_update, telegram_context):
    """Test handling a message that's not a SciArticle request."""
    # Setup
    telegram_update.message.text = "Just a regular message"
    
    # Execute
    await handle_request(telegram_update, telegram_context)
    
    # Verify
    # Check that no message was sent (handler should return early)
    telegram_context.bot.send_message.assert_not_called()
