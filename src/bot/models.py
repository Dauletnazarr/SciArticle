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

    request = models.ForeignKey(Request, on_delete=models.CASCADE)
    file = models.FileField(upload_to='pdfs/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    validated_at = models.DateTimeField(null=True)
    is_valid = models.BooleanField(null=True)
    delete_at = models.DateTimeField(null=True)

    class Meta:
        verbose_name = 'загрузка PDF'
        verbose_name_plural = 'Загрузки PDF'

    def save(self, *args, **kwargs):
        if not self.pk:
            self.delete_at = self.validated_at + timedelta(days=3)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.file} {self.uploaded_at}'


class Validation(models.Model):
    """Валидация PDF."""

    pdf_upload = models.ForeignKey(PDFUpload, on_delete=models.CASCADE)
    user_id = models.BigIntegerField()
    vote = models.BooleanField()
    voted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
                models.UniqueConstraint(
                    fields=['pdf_upload', 'user_id'],
                    name='unique_upload'
                )
            ]
        verbose_name = 'валидация'
        verbose_name_plural = 'Валидации'

    def __str__(self):
        return f'{self.user_id} {self.pdf_upload}'


class User(AbstractUser):
    """Пользователь."""

    telegram_id = models.BigIntegerField(unique=True)
    username = models.CharField(max_length=25, unique=True, null=True)
    is_in_bot = models.BooleanField()
    uploads_count = models.BigIntegerField()
    validations_count = models.BigIntegerField()

    class Meta:
        verbose_name = 'пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return f'{self.telegram_id} {self.username}'


class Notification(models.Model):
    """Уведомление."""

    user = models.ForeignKey(User, on_delete=models.CASCADE)
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
            self.delete_at = self.delete_at + timedelta(hours=1)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.type} {self.created_at}'


class Subscription(models.Model):
    """Подписка."""

    user = models.ForeignKey(User, on_delete=models.CASCADE)
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
    """Конфигурация."""

    key = models.CharField(max_length=256)
    value = models.IntegerField()

    class Meta:
        verbose_name = 'конфигурация'
        verbose_name_plural = 'Конфигурации'

    def __str__(self):
        return f'{self.key} {self.value}'
