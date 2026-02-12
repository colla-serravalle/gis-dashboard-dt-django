"""URL configuration for reports app - API views."""

from django.urls import path
from .views.api import get_data, get_filter_options, image_proxy

app_name = 'reports_api'

urlpatterns = [
    path('data/', get_data, name='get_data'),
    path('filters/', get_filter_options, name='get_filters'),
    path('image/<int:layer>/<int:object_id>/<int:attachment_id>/', image_proxy, name='image_proxy'),
]
