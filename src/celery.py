import os

from celery import Celery

# Set default Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sciarticle.settings')

app = Celery('sciarticle')

# Use Django settings for Celery
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load tasks from all registered Django app configs
app.autodiscover_tasks()

# Configure Redis as the broker and result backend
app.conf.broker_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
app.conf.result_backend = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

# Task settings
app.conf.task_serializer = 'json'
app.conf.accept_content = ['json']
app.conf.result_serializer = 'json'
app.conf.task_time_limit = 30 * 60  # 30 minutes
app.conf.task_soft_time_limit = 15 * 60  # 15 minutes
app.conf.worker_hijack_root_logger = False

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
