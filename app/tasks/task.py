import datetime
import logging
# Импорт приложения Celery и настроек из config.py
from app.celery_app import celery_app
from app.config import PDF_REQUEST_LIFETIME

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def cleanup_pdf_requests(self):
    """
    Задача для очистки устаревших запросов на PDF.

    Согласно ТЗ, запросы на PDF удаляются через 3 дня после создания.
    Здесь реализуется логика удаления таких записей из БД.
    """
    try:
        now = datetime.datetime.utcnow()
        threshold = now - datetime.timedelta(seconds=PDF_REQUEST_LIFETIME)

        # Пример работы с ORM:
        # from app.models import PDFRequest
        # from app.database import SessionLocal
        # session = SessionLocal()
        # deleted_count = session.query(PDFRequest).filter(PDFRequest.created_at < threshold).delete()
        # session.commit()
        # session.close()

        logger.info(f"Удалены PDF запросы, созданные до {threshold}.")
        return f"Удалено устаревших PDF запросов, созданных до {threshold}."
    except Exception as exc:
        logger.error("Ошибка при очистке PDF запросов", exc_info=True)
        raise self.retry(exc=exc)

@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def process_doi_request(self, doi):
    """
    Задача для обработки DOI-запроса.

    При получении DOI (например, '10.1000/xyz123') задача должна:
      - Выполнить запрос к внешнему API для получения метаданных статьи.
      - Обновить запись в БД, связанную с данным запросом.

    Это необходимо для реализации функционала «Запросы по DOI через бота».
    """
    try:
        # Пример запроса к API CrossRef:
        # import requests
        # response = requests.get(f"https://api.crossref.org/works/{doi}")
        # data = response.json()
        # Здесь необходимо обновить данные запроса в БД с полученными метаданными.

        logger.info(f"Обработка запроса по DOI: {doi}")
        return f"Метаданные для DOI {doi} успешно обработаны."
    except Exception as exc:
        logger.error(f"Ошибка при обработке DOI запроса {doi}", exc_info=True)
        raise self.retry(exc=exc)

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_reward_notification(self, user_id, reward_type, count):
    """
    Задача для отправки уведомления о вознаграждении.

    После загрузки PDF или проверки статьи пользователю должно отправляться уведомление,
    информирующее о накопленных достижениях и начислении подписки.

    Параметры:
      user_id (int): идентификатор пользователя (chat_id в Telegram)
      reward_type (str): тип вознаграждения ('upload' для загрузок, 'validation' для проверок)
      count (int): количество достижений, необходимых для получения подписки
    """
    try:
        # Пример отправки сообщения через python-telegram-bot:
        # from app.bot.telegram_bot import bot
        # message = f"Поздравляем! Вы достигли {count} {reward_type}. Ваша подписка активирована/продлена."
        # bot.send_message(chat_id=user_id, text=message)

        logger.info(f"Отправлено уведомление пользователю {user_id}: тип {reward_type}, счет {count}")
        return f"Уведомление отправлено пользователю {user_id} за {reward_type}."
    except Exception as exc:
        logger.error(f"Ошибка при отправке уведомления для пользователя {user_id}", exc_info=True)
        raise self.retry(exc=exc)

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def clear_chat_messages(self):
    """
    Задача для очистки устаревших сообщений в чате.

    Согласно ТЗ, сообщения (например, уведомления о проверках или загрузках)
    удаляются через заданный интервал (например, через 1 час для уведомлений, через 3 дня для других сообщений).

    Здесь реализуется логика удаления сообщений, удовлетворяющих указанным временным условиям.
    """
    try:
        now = datetime.datetime.utcnow()

        # Пример удаления сообщений через ORM:
        # from app.models import ChatMessage
        # from app.database import SessionLocal
        # session = SessionLocal()
        # one_hour_ago = now - datetime.timedelta(hours=1)
        # session.query(ChatMessage).filter(ChatMessage.created_at < one_hour_ago,
        #                                     ChatMessage.type == 'notification').delete()
        # session.commit()
        # session.close()

        logger.info("Очистка устаревших сообщений в чате выполнена.")
        return "Очистка чата завершена."
    except Exception as exc:
        logger.error("Ошибка при очистке чата", exc_info=True)
        raise self.retry(exc=exc)
