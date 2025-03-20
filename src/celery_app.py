from celery import Celery

from src.config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND

# Инициализация Celery
celery_app = Celery(
    "SciArticle", broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND
)

# Обновление конфигурации Celery
celery_app.conf.update(
    task_routes={
        # Указываем, что задача example_task должна выполняться в очереди "default"
        "app.tasks.example_task.example_task": {"queue": "default"},
    },
    worker_concurrency=4,  # Количество параллельных процессов
    task_time_limit=300,  # Жёсткий лимит времени выполнения задачи (в секундах)
    task_soft_time_limit=240,  # Мягкий лимит времени, после которого начинается предупреждение
)
