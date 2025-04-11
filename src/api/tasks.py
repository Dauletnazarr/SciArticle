import requests
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

from bot.models import Request


@shared_task
def process_doi_request(request_id):
    """
    Task to process a DOI request.
    It fetches the DOI URL, and based on the HTTP response,
    updates the request status.
    """
    try:
        doi_request = Request.objects.get(id=request_id)
        # For example, perform an HTTP GET request to the DOI URL.
        response = requests.get(doi_request.doi)

        # Update status based on response.
        if response.status_code == 200:
            doi_request.status = 'completed'
        else:
            doi_request.status = 'expired'
        doi_request.save()

    except Request.DoesNotExist:
        # If the request record was deleted.
        print(f"DOI request with id {request_id} does not exist.")
    except Exception as e:
        # You can use Django logging here.
        print(f"Error processing DOI request {request_id}: {str(e)}")
