from django.conf import settings
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from telegram import Bot
from .models import Config, Subscription


def check_and_award_subscription(chat_user):
    """
    Проверяет, достиг ли пользователь порога загрузок (Z) или проверок (H),
    и выдаёт подписку, если достиг.
    """
    config = Config.objects.first()
    if not config:
        return False

    awarded = False

    # Порог загрузок (Z)
    z = config.uploads_for_subscription
    if z and chat_user.upload_count and chat_user.upload_count % z == 0:
        award_subscription(chat_user, reason='uploads')
        awarded = True

    # Порог проверок (H)
    h = config.validations_for_subscription
    if h and chat_user.validation_count and chat_user.validation_count % h == 0:
        award_subscription(chat_user, reason='validations')
        awarded = True

    return awarded


def award_subscription(chat_user, reason):
    """
    Создаёт запись Subscription и уведомляет пользователя через Telegram.
    """
    # Определяем дату начала подписки: либо сейчас, либо конец предыдущей
    last = Subscription.objects.filter(user=chat_user).order_by('-end_date').first()
    start_date = timezone.now()
    if last and last.end_date > start_date:
        start_date = last.end_date

    # Продление на 1 месяц
    end_date = start_date + relativedelta(months=1)

    sub = Subscription.objects.create(
        user=chat_user,
        start_date=start_date,
        end_date=end_date,
        reason=reason
    )

    # Отправляем уведомление через Telegram Bot
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    if chat_user.has_bot:
        bot.send_message(
            chat_id=chat_user.user_id,
            text=(f"🎉 Поздравляем! Вам выдана подписка до {end_date.date()}"
                  f" за {reason}.")
        )
    # TODO: при необходимости уведомить основной бот SciSourceBot через API
    return sub
