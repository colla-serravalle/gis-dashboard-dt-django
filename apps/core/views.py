"""Core application views."""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views import View
from django.utils.decorators import method_decorator


@method_decorator(login_required, name='dispatch')
class HomeView(View):
    """Home page view - main dashboard for all services."""

    template_name = 'core/home.html'

    def get(self, request):
        return render(request, self.template_name)
