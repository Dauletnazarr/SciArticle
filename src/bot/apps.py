from django.apps import AppConfig


class ChatConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chat'
    verbose_name = 'Telegram Chat'

    def ready(self):
        # При старте приложения регистрируем сигналы
        import chat.signals