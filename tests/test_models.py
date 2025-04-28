from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from bot.models import (
    ChatUser,
    Config,
    Notification,
    PDFUpload,
    Request,
    Subscription,
    Validation,
)


@pytest.mark.django_db
class TestChatUser:
    def test_create_chat_user(self, chat_user):
        """Test creating a ChatUser."""
        assert chat_user.telegram_id == 123456789
        assert chat_user.username == "test_user"
        assert chat_user.is_in_bot is True
        assert chat_user.upload_count == 0
        assert chat_user.validation_count == 0

    def test_str_representation(self, chat_user):
        """Test the string representation of a ChatUser."""
        assert str(chat_user) == "123456789 test_user"


@pytest.mark.django_db
class TestRequest:
    def test_create_request(self, request_obj):
        """Test creating a Request."""
        assert request_obj.doi == "10.1234/test.doi"
        assert request_obj.status == "pending"
        assert request_obj.chat_id == 123456789
        assert request_obj.user.telegram_id == 123456789

    def test_auto_expiry_date(self):
        """Test that expires_at is automatically set."""
        now = timezone.now()
        request = Request.objects.create(
            doi="10.5678/test.doi",
            status="pending",
            chat_id=123456789
        )
        assert request.expires_at.date() == (now + timedelta(days=3)).date()

    def test_str_representation(self, request_obj):
        """Test the string representation of a Request."""
        assert str(request_obj).startswith("10.1234/test.doi")


@pytest.mark.django_db
class TestPDFUpload:
    def test_create_pdf_upload(self, pdf_upload):
        """Test creating a PDFUpload."""
        assert pdf_upload.file == "test_file.pdf"
        assert pdf_upload.chat_message_id == 123456
        assert pdf_upload.user.telegram_id == 123456789
        assert pdf_upload.request.doi == "10.1234/test.doi"

    def test_auto_delete_at(self):
        """Test that delete_at is set when validated_at is provided."""
        now = timezone.now()
        request = Request.objects.create(
            doi="10.5678/test.doi",
            status="pending",
            chat_id=123456789
        )
        user = ChatUser.objects.create(
            telegram_id=111222333,
            username="test_user2"
        )
        pdf = PDFUpload.objects.create(
            request=request,
            file="test_file2.pdf",
            chat_message_id=654321,
            user=user,
            validated_at=now
        )
        assert pdf.delete_at.date() == (now + timedelta(days=3)).date()

    def test_str_representation(self, pdf_upload):
        """Test the string representation of a PDFUpload."""
        assert str(pdf_upload).startswith("test_file.pdf")


@pytest.mark.django_db
class TestValidation:
    def test_create_validation(self, validation):
        """Test creating a Validation."""
        assert validation.vote is True
        assert validation.user.telegram_id == 987654321
        assert validation.pdf_upload.file == "test_file.pdf"

    def test_prevent_self_validation(self, pdf_upload, chat_user):
        """Test that a user cannot validate their own upload."""
        validation = Validation(
            pdf_upload=pdf_upload,
            user=chat_user,
            vote=True
        )
        with pytest.raises(ValidationError):
            validation.clean()

    def test_prevent_requester_validation(self, pdf_upload, chat_user):
        """Test that a request creator cannot validate uploads for their request."""
        validation = Validation(
            pdf_upload=pdf_upload,
            user=chat_user,
            vote=True
        )
        with pytest.raises(ValidationError):
            validation.clean()

    def test_str_representation(self, validation, another_chat_user, pdf_upload):
        """Test the string representation of a Validation."""
        expected = f"{another_chat_user} {pdf_upload}"
        assert str(validation) == expected


@pytest.mark.django_db
class TestConfig:
    def test_create_config(self, config):
        """Test creating a Config."""
        assert config.uploads_for_subscription == 10
        assert config.validations_for_subscription == 20

    def test_get_instance(self):
        """Test the get_instance class method."""
        Config.objects.all().delete()

        config1 = Config.get_instance()
        assert config1.pk == 1

        config2 = Config.get_instance()
        assert config2.pk == 1
        assert config1 == config2


@pytest.mark.django_db
class TestNotification:
    def test_create_notification(self, chat_user):
        """Test creating a Notification."""
        notification = Notification.objects.create(
            user=chat_user,
            type="upload",
            chat_message_id=123456
        )
        assert notification.user == chat_user
        assert notification.type == "upload"
        assert notification.chat_message_id == 123456

        assert notification.delete_at.hour == (notification.created_at + timedelta(hours=1)).hour

    def test_str_representation(self, chat_user):
        """Test the string representation of a Notification."""
        notification = Notification.objects.create(
            user=chat_user,
            type="upload",
            chat_message_id=123456
        )
        assert str(notification).startswith("upload")


@pytest.mark.django_db
class TestSubscription:
    def test_create_subscription(self, chat_user):
        """Test creating a Subscription."""
        end_date = timezone.now() + timedelta(days=30)
        subscription = Subscription.objects.create(
            user=chat_user,
            end_date=end_date,
            reason="uploads"
        )
        assert subscription.user == chat_user
        assert subscription.reason == "uploads"
        assert subscription.end_date.date() == end_date.date()

    def test_str_representation(self, chat_user):
        """Test the string representation of a Subscription."""
        end_date = timezone.now() + timedelta(days=30)
        subscription = Subscription.objects.create(
            user=chat_user,
            end_date=end_date,
            reason="uploads"
        )
        assert str(subscription).startswith(str(chat_user))
