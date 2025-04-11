from django.urls import path
from .views import create_doi_request

urlpatterns = [
    path('request/', create_doi_request, name='create_doi_request'),
]