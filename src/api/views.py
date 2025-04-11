# articles/views.py
from datetime import timedelta
from django.http import JsonResponse
from django.utils import timezone

from bot.models import Request
from api.tasks import process_doi_request


def create_doi_request(request):
    """
    Example view for creating a DOI request.
    Expects GET (or POST) parameters: user_id and doi.
    """
    user_id = request.GET.get('user_id')
    doi_url = request.GET.get('doi')

    if not user_id or not doi_url:
        return JsonResponse({
            'status': 'error',
            'message': 'Parameters "user_id" and "doi" are required.'
        }, status=400)

    # Create the DOI request record.
    doi_request = Request.objects.create(
        doi=doi_url,
        chat_id=int(user_id),
        status='pending',
        expires_at=timezone.now() + timedelta(days=3)
    )

    # Enqueue background task to process the DOI request.
    process_doi_request.delay(doi_request.id)

    return JsonResponse({
        'status': 'pending',
        'request_id': doi_request.id,
        'message': 'DOI request has been received and is being processed.'
    })
