from src.common.celery_app import celery_app

@celery_app.task
def add_numbers(x, y):
    return x + y
