import os

import django

# must be here or else django throws an error
# django.core.exceptions.AppRegistryNotReady: Apps aren't loaded yet.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dtb.settings')
django.setup()

from telegram.ext import Updater

from dtb.settings import TELEGRAM_TOKEN
from tgbot.dispatcher import setup_dispatcher
from tgbot.main import TELEGRAM_BOT_USERNAME


def run_polling(tg_token: str = TELEGRAM_TOKEN):
    """Run bot in polling mode"""
    updater = Updater(tg_token, use_context=True)

    dp = updater.dispatcher
    dp = setup_dispatcher(dp)

    bot_link = f'https://t.me/{TELEGRAM_BOT_USERNAME}'

    print(f'Polling of '{bot_link}' has started')
    # it is really useful to send '👋' emoji to developer
    # when you run local test
    # bot.send_message(text='👋', chat_id=<YOUR TELEGRAM ID>)

    updater.start_polling()


if __name__ == '__main__':
    run_polling()
