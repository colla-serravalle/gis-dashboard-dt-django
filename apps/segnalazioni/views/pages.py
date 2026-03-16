"""Page views for segnalazioni app."""

from django.shortcuts import render
from django.views import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.conf import settings


@method_decorator(login_required, name='dispatch')
class SegnalazioniListView(View):
    """Segnalazioni list view with filtering, sorting, and pagination."""

    template_name = 'segnalazioni/segnalazioni_list.html'

    def get(self, request):
        context = {
            'items_per_page': getattr(settings, 'ITEMS_PER_PAGE', 10),
        }
        return render(request, self.template_name, context)
