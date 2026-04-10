"""Page views for reports app."""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.views import View
from django.utils.decorators import method_decorator
from django.conf import settings

from apps.reports.mappings import get_field_label
from apps.reports.services.report_data import get_report_data
from apps.audit.utils import emit_audit_event
from config.strings import UI_STRINGS


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

        emit_audit_event(request, "data.report.viewed", detail={"report_id": None})
        return render(request, self.template_name, context)


@method_decorator(login_required, name='dispatch')
class ReportDetailView(View):
    """Report detail view."""

    template_name = 'reports/report_detail.html'

    def get(self, request):
        report_id = request.GET.get('id')

        if not report_id:
            return redirect('reports:report_list')

        try:
            data = get_report_data(report_id)
        except ValueError:
            return HttpResponseBadRequest(UI_STRINGS['error_invalid_report_id'])

        if data is None:
            return render(request, self.template_name, {
                'error': UI_STRINGS['error_record_not_found']
            })

        emit_audit_event(request, "data.report.viewed", detail={"report_id": report_id})
        return render(request, self.template_name, data)
