"""URL configuration for core app - general application routes."""

from django.urls import path
from .views import HomeView

app_name = 'core'

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
]
