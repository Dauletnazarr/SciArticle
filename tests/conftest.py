import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

import django
import pytest

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tests.settings')
django.setup()

from bot.models import ChatUser, Config, PDFUpload, Request, Validation


@pytest.fixture
def chat_user():
    """Create a test ChatUser."""
    user = ChatUser.objects.create(
        telegram_id=123456789,
        username="test_user",
        is_in_bot=True,
        upload_count=0,
        validation_count=0
    )
    return user


@pytest.fixture
def another_chat_user():
    """Create another test ChatUser."""
    user = ChatUser.objects.create(
        telegram_id=987654321,
        username="another_user",
        is_in_bot=True,
        upload_count=0,
        validation_count=0
    )
    return user


@pytest.fixture
def request_obj(chat_user):
    """Create a test Request."""
    request = Request.objects.create(
        doi="10.1234/test.doi",
        status="pending",
        chat_id=123456789,
        user=chat_user
    )
    return request


@pytest.fixture
def pdf_upload(request_obj, chat_user):
    """Create a test PDFUpload."""
    pdf = PDFUpload.objects.create(
        request=request_obj,
        file="test_file.pdf",
        chat_message_id=123456,
        user=chat_user
    )
    return pdf


@pytest.fixture
def validation(pdf_upload, another_chat_user):
    """Create a test Validation."""
    validation = Validation.objects.create(
        pdf_upload=pdf_upload,
        user=another_chat_user,
        vote=True
    )
    return validation


@pytest.fixture
def config():
    """Create a test Config."""
    config = Config.objects.create(
        uploads_for_subscription=10,
        validations_for_subscription=20
    )
    return config
