"""URL configuration for reports app - page views."""

from django.urls import path
from .views.pages import HomeView, ReportListView, ReportDetailView

app_name = 'reports'

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('reports/', ReportListView.as_view(), name='report_list'),
    path('reports/detail/', ReportDetailView.as_view(), name='report_detail'),
]
