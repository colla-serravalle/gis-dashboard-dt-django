"""Page views for segnalazioni app."""

from django.shortcuts import render
from django.views import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.conf import settings

from apps.audit.utils import emit_audit_event


@method_decorator(login_required, name='dispatch')
class SegnalazioniListView(View):
    """Segnalazioni list view with filtering, sorting, and pagination."""

    template_name = 'segnalazioni/segnalazioni_list.html'

    def get(self, request):
        context = {
            'items_per_page': getattr(settings, 'ITEMS_PER_PAGE', 10),
        }
        emit_audit_event(request, "data.segnalazione.viewed", detail={"segnalazione_id": None})
        return render(request, self.template_name, context)
