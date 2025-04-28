from src.sciarticle.settings import * # noqa F403

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Make Celery execute tasks synchronously for testing
CELERY_TASK_ALWAYS_EAGER = True