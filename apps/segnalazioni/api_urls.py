"""URL configuration for segnalazioni app - API views."""

from django.urls import path
from .views.api import get_data, get_filter_options

app_name = 'segnalazioni_api'

urlpatterns = [
    path('data/', get_data, name='get_data'),
    path('filters/', get_filter_options, name='get_filters'),
]
