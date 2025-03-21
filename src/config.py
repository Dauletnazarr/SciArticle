import os

# -----------------------
# Настройки Redis для Celery
# -----------------------
REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", "")
REDIS_DB_BROKER = int(os.environ.get("REDIS_DB_BROKER", 0))
REDIS_DB_BACKEND = int(os.environ.get("REDIS_DB_BACKEND", 1))

CELERY_BROKER_URL = (
    f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB_BROKER}"
)
CELERY_RESULT_BACKEND = (
    f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB_BACKEND}"
)

# -----------------------
# Настройки Telegram бота
# -----------------------
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "your_bot_token_here")

# -----------------------
# Настройки PostgreSQL (если требуется для работы с данными)
# -----------------------
POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "5432")
POSTGRES_DB = os.environ.get("POSTGRES_DB", "sciarticle_db")
POSTGRES_USER = os.environ.get("POSTGRES_USER", "user")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "password")
DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# -----------------------
# Прочие настройки проекта
# -----------------------
DEBUG = os.environ.get("DEBUG", "False").lower() in ("true", "1", "t")

# Временные интервалы (см. требования по удалению запросов и PDF из БД)
PDF_REQUEST_LIFETIME = 3 * 24 * 3600  # 3 дня в секундах для хранения запросов на PDF
PDF_VALIDATION_INTERVAL = (
    60 * 60
)  # Пример интервала для периодических проверок (например, 1 час)
