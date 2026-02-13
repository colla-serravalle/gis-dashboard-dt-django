"""Page views for reports app."""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views import View
from django.utils.decorators import method_decorator
from django.conf import settings

from apps.reports.mappings import get_field_label
from apps.reports.services.report_data import get_report_data


@method_decorator(login_required, name='dispatch')
class HomeView(View):
    """Home page view."""

    template_name = 'reports/home.html'

    def get(self, request):
        return render(request, self.template_name)


@method_decorator(login_required, name='dispatch')
class ReportListView(View):
    """Report list view with filtering, sorting, and pagination."""

    template_name = 'reports/report_list.html'

    def get(self, request):
        items_per_page = getattr(settings, 'ITEMS_PER_PAGE', 10)

        context = {
            'items_per_page': items_per_page,
            'labels': {
                'nome_operatore': get_field_label('nome_operatore'),
                'tratta': get_field_label('tratta'),
                'tipologia_appalto': get_field_label('tipologia_appalto'),
                'data_rilevamento': get_field_label('data_rilevamento'),
            }
        }

        return render(request, self.template_name, context)


@method_decorator(login_required, name='dispatch')
class ReportDetailView(View):
    """Report detail view."""

    template_name = 'reports/report_detail.html'

    def get(self, request):
        report_id = request.GET.get('id')

        if not report_id:
            return redirect('reports:report_list')

        data = get_report_data(report_id)

        if data is None:
            return render(request, self.template_name, {
                'error': 'Record non trovato'
            })

        return render(request, self.template_name, data)
