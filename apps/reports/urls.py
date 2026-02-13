"""URL configuration for reports app - page views."""

from django.urls import path
from .views.pages import ReportListView, ReportDetailView
from .views.pdf import export_pdf

app_name = 'reports'

urlpatterns = [
    path('reports/', ReportListView.as_view(), name='report_list'),
    path('reports/detail/', ReportDetailView.as_view(), name='report_detail'),
    path('reports/pdf/', export_pdf, name='report_pdf'),
]
