"""URL configuration for core app - general application routes."""

from django.urls import path
from .views import ProfileView

app_name = 'profiles'

urlpatterns = [
    path('profiles/', ProfileView.as_view(), name='profile'),
]
