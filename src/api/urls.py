from django.urls import path
from .views import create_article_request

urlpatterns = [
    path('request/', create_article_request, name='create_article_request'),
]