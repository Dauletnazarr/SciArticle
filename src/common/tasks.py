import requests
from celery import shared_task



@shared_task
def example_task(url):
    """Example Celery task that fetches a URL."""
    response = requests.get(url)
    return response.status_code

