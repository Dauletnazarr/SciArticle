from bot.models import Config
from sciarticle.settings import TELEGRAM_BOT_TOKEN
from src.celery import app  # наш Celery объект

config = Config.objects.first()
Z = config.uploads_for_subscription
H = config.validations_for_subscription


@app.task
def delete_message_task(chat_id, message_id):
    from telegram import Bot
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    try:
        bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        # возможно, сообщение уже удалено или истекло время на удаление
        print(f"Failed to delete message {message_id}: {e}")

def schedule_pdf_deletion(chat_id: int, message_id: int, delay: int):
    # Запланировать задачу через Celery
    delete_message_task.apply_async(args=[chat_id, message_id], countdown=delay)

def schedule_notification_deletion(chat_id: int, message_id: int, delay: int):
    delete_message_task.apply_async(args=[chat_id, message_id], countdown=delay)

