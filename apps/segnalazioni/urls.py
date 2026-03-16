"""URL configuration for segnalazioni app - page views."""

from django.urls import path
from .views import SegnalazioniListView

app_name = 'segnalazioni'

urlpatterns = [
    path('segnalazioni/', SegnalazioniListView.as_view(), name='segnalazioni_list'),
]
