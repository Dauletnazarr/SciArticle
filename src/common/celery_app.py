# src/common/celery_app.py
import os
from celery import Celery

# Point Celery to your Django settings module.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sciarticle.settings")

app = Celery("sciarticle")

# Read configuration from Django settings, using a 'CELERY_' prefix
app.config_from_object("django.conf:settings", namespace="CELERY")

# Autodiscover tasks from installed apps (including any 'tasks.py' files).
app.autodiscover_tasks()
