from unittest.mock import MagicMock, patch

import pytest

from bot.models import Config
from bot.tasks import delete_message_task, schedule_notification_deletion, schedule_pdf_deletion


@pytest.fixture
def mock_bot():
    """Create a mock Telegram Bot."""
    with patch('telegram.Bot') as mock_bot_class:
        mock_bot_instance = MagicMock()
        mock_bot_class.return_value = mock_bot_instance
        yield mock_bot_instance


@pytest.mark.django_db
class TestDeleteMessageTask:
    @patch('bot.tasks.Bot')
    def test_delete_message_success(self, mock_bot_class, mock_bot):
        """Test successful message deletion."""
        mock_bot_class.return_value = mock_bot
        chat_id = 123456789
        message_id = 987654321

        delete_message_task(chat_id, message_id)

        mock_bot.delete_message.assert_called_once_with(
            chat_id=chat_id,
            message_id=message_id
        )

    @patch('bot.tasks.Bot')
    @patch('bot.tasks.print')
    def test_delete_message_failure(self, mock_print, mock_bot_class, mock_bot):
        """Test handling of message deletion failure."""
        mock_bot_class.return_value = mock_bot
        chat_id = 123456789
        message_id = 987654321
        error_message = "Message to delete not found"
        mock_bot.delete_message.side_effect = Exception(error_message)

        delete_message_task(chat_id, message_id)

        mock_bot.delete_message.assert_called_once_with(
            chat_id=chat_id,
            message_id=message_id
        )
        mock_print.assert_called_once()
        args, _ = mock_print.call_args
        assert f"Failed to delete message {message_id}" in args[0]
        assert error_message in args[0]


@pytest.mark.django_db
class TestScheduleFunctions:
    @patch('bot.tasks.delete_message_task')
    def test_schedule_pdf_deletion(self, mock_delete_task):
        """Test scheduling PDF deletion."""
        chat_id = 123456789
        message_id = 987654321
        delay = 259200

        schedule_pdf_deletion(chat_id, message_id, delay)

        mock_delete_task.apply_async.assert_called_once_with(
            args=[chat_id, message_id],
            countdown=delay
        )

    @patch('bot.tasks.delete_message_task')
    def test_schedule_notification_deletion(self, mock_delete_task):
        """Test scheduling notification deletion."""
        chat_id = 123456789
        message_id = 987654321
        delay = 3600

        schedule_notification_deletion(chat_id, message_id, delay)

        mock_delete_task.apply_async.assert_called_once_with(
            args=[chat_id, message_id],
            countdown=delay
        )


@pytest.mark.django_db
class TestConfigAccess:
    def test_config_access(self, config):
        """Test accessing Config values."""
        assert config.uploads_for_subscription == 10
        assert config.validations_for_subscription == 20

        instance = Config.get_instance()
        assert instance is not None
        assert instance.uploads_for_subscription == 10
        assert instance.validations_for_subscription == 20
