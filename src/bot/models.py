from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

STATUS = (
    ('pending', 'pending'),
    ('completed', 'completed'),
    ('expired', 'expired')
)

TYPE = (
    ('upload', 'upload'),
    ('validation', 'validation')
)

REASON = (
    ('uploads', 'uploads'),
    ('validations', 'validations')
)


class ChatUser(AbstractUser):
    """Пользователь."""

    telegram_id = models.BigIntegerField(unique=True, null=True, blank=True)
    username = models.CharField(max_length=25, unique=True, null=True)
    join_date = models.DateTimeField(auto_now_add=True)
    is_in_bot = models.BooleanField(default=False, help_text="Whether user has interacted with the bot directly")
    upload_count = models.BigIntegerField(default=0)
    validation_count = models.BigIntegerField(default=0)

    class Meta:
        verbose_name = 'пользователь'
        verbose_name_plural = 'Пользователи'
        app_label = "bot"

    def __str__(self):
        return f'{self.telegram_id} {self.username}'


class Request(models.Model):
    """Запрос на PDF."""

    doi = models.CharField(max_length=256, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    status = models.CharField(
        max_length=25,
        choices=STATUS,
    )
    chat_id = models.BigIntegerField()
    user = models.ForeignKey(ChatUser, on_delete=models.SET_NULL, null=True, blank=True,
                            related_name='requests')
    request_message_id = models.BigIntegerField(
        help_text="Telegram message_id, в ответ на которое пользователь делал /request"
    )

    class Meta:
        verbose_name = 'запрос'
        verbose_name_plural = 'Запросы'

    def save(self, *args, **kwargs):
        if not self.pk:
            self.created_at = timezone.now()
            self.expires_at = self.created_at + timedelta(days=3)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.doi} {self.created_at}'


class PDFUpload(models.Model):
    """Загрузка PDF."""

    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name='uploads')
    file = models.FileField(upload_to='pdfs/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    validated_at = models.DateTimeField(null=True, blank=True)
    is_valid = models.BooleanField(null=True, blank=True)
    delete_at = models.DateTimeField(null=True, blank=True)
    chat_message_id = models.BigIntegerField()
    user = models.ForeignKey(ChatUser, on_delete=models.CASCADE, related_name='uploads')

    class Meta:
        verbose_name = 'загрузка PDF'
        verbose_name_plural = 'Загрузки PDF'

    def save(self, *args, **kwargs):
        if not self.pk:
            if self.validated_at:
                self.delete_at = self.validated_at + timedelta(days=3)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.file} {self.uploaded_at}'


class Validation(models.Model):
    """Валидация PDF."""

    pdf_upload = models.ForeignKey(PDFUpload, on_delete=models.CASCADE, related_name='validations')
    user = models.ForeignKey(ChatUser, on_delete=models.CASCADE, related_name='validations')
    vote = models.BooleanField()
    voted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['pdf_upload', 'user'],
                name='unique_upload'
            ),
        ]
        verbose_name = 'валидация'
        verbose_name_plural = 'Валидации'

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.user == self.pdf_upload.user:
            raise ValidationError("Users cannot validate their own uploads")
        if self.user == self.pdf_upload.request.user:
            raise ValidationError("Request creators cannot validate uploads for their own requests")

    def __str__(self):
        return f'{self.user} {self.pdf_upload}'


class Notification(models.Model):
    """Уведомление."""

    user = models.ForeignKey(ChatUser, on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(
        max_length=25,
        choices=TYPE,
    )
    chat_message_id = models.BigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    delete_at = models.DateTimeField()

    class Meta:
        verbose_name = 'уведомление'
        verbose_name_plural = 'Уведомления'

    def save(self, *args, **kwargs):
        if not self.pk:
            self.delete_at = self.created_at + timedelta(hours=1)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.type} {self.created_at}'


class Subscription(models.Model):
    """Подписка."""

    user = models.ForeignKey(ChatUser, on_delete=models.CASCADE, related_name='subscriptions')
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()
    reason = models.CharField(
        max_length=25,
        choices=REASON,
    )

    class Meta:
        verbose_name = 'подписка'
        verbose_name_plural = 'Подписки'

    def __str__(self):
        return f'{self.user} {self.start_date}'


class Config(models.Model):
    """Model for storing configurable threshold values and other parameters.
    Designed to have only one instance that can be edited through Django Admin.
    """

    uploads_for_subscription = models.PositiveIntegerField(
        default=10,
        help_text="Number of uploads required to earn a subscription"
    )

    validations_for_subscription = models.PositiveIntegerField(
        default=20,
        help_text="Number of validations (votes) required to earn a subscription"
    )

    class Meta:
        verbose_name = "Configuration"
        verbose_name_plural = "Configuration"

    @classmethod
    def get_instance(cls):
        """Get the singleton instance of Config, creating it if it doesn't exist.
        This ensures there's always a configuration available.
        """
        instance, created = cls.objects.get_or_create(pk=1)
        return instance
