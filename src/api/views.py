from django.shortcuts import render

from datetime import timedelta
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from src.bot.models import Request

@require_http_methods(["GET"])
def create_article_request(request):
    """
    Эндпоинт для создания записи-запроса.
    Ожидает GET-параметры: user_id и doi (с полным URL).
    Если не передан источник, используем значение по умолчанию "SciArticle Search".
    """
    user_id = request.GET.get('user_id')
    doi_url = request.GET.get('doi')

    # Проверка обязательных параметров
    if not user_id or not doi_url:
        return JsonResponse({
            'status': 'error',
            'message': 'Необходимые параметры: user_id и doi.'
        }, status=400)

    try:
        # Создаем новый запрос
        new_request = Request(
            doi=doi_url,
            chat_id=int(user_id),
            status='pending',
            # В save() поле expires_at должно установиться автоматически,
            # но можно задать его заранее, если требуется:
            expires_at=timezone.now() + timedelta(days=3)
        )
        new_request.save()
        return JsonResponse({
            'status': 'success',
            'record_id': new_request.id,
            'message': 'Запрос на статью создан.'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)
