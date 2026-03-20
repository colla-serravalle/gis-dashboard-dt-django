"""Authentication views."""

import time
import logging
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.conf import settings
from django.views import View

from .forms import LoginForm
from apps.audit.utils import emit_audit_event

logger = logging.getLogger(__name__)


class LoginView(View):
    """Login view with rate limiting support."""

    template_name = 'accounts/login.html'

    def get(self, request):
        """Display login form."""
        # If already logged in, redirect to home
        if request.user.is_authenticated:
            return redirect('core:home')

        # Handle error messages from query params
        error = request.GET.get('error')
        timeout = request.GET.get('timeout')

        error_message = None
        if error == 'csrf':
            error_message = 'Token di sicurezza non valido. Riprova.'
        elif error == 'locked':
            error_message = 'Troppi tentativi di login. Account temporaneamente bloccato.'
        elif error == 'credentials':
            error_message = 'Username e/o password errati!'
        elif error == 'session_invalid':
            error_message = 'Sessione non valida. Effettua nuovamente il login.'
        elif timeout == '1':
            error_message = 'Sessione scaduta per inattività. Effettua nuovamente il login.'

        form = LoginForm()

        return render(request, self.template_name, {
            'form': form,
            'error_message': error_message,
        })

    def post(self, request):
        """Process login form submission."""
        form = LoginForm(request.POST)

        # Check rate limiting
        login_attempts = request.session.get('login_attempts', 0)
        last_attempt = request.session.get('last_attempt', 0)
        max_attempts = getattr(settings, 'MAX_LOGIN_ATTEMPTS', 5)
        lockout_duration = getattr(settings, 'LOCKOUT_DURATION', 900)

        current_time = time.time()

        # Check if account is locked
        if login_attempts >= max_attempts:
            time_passed = current_time - last_attempt
            if time_passed < lockout_duration:
                emit_audit_event(request, "auth.login.locked", detail={
                    "username_attempted": request.POST.get("username", ""),
                    "attempt_count": login_attempts,
                    "locked_until": last_attempt + lockout_duration,
                })
                return redirect('/auth/login/?error=locked')
            else:
                # Reset counter after lockout period
                request.session['login_attempts'] = 0

        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = authenticate(request, username=username, password=password)

            if user is not None:
                # Login successful
                request.session['login_attempts'] = 0
                login(request, user)

                emit_audit_event(request, "auth.login.success", detail={"auth_method": "local"})

                # Redirect to next URL or home
                next_url = request.GET.get('next', '/')
                return redirect(next_url)
            else:
                # Login failed
                request.session['login_attempts'] = login_attempts + 1
                request.session['last_attempt'] = current_time

                emit_audit_event(request, "auth.login.failure", detail={
                    "username_attempted": username,
                    "attempt_count": login_attempts + 1,
                })

                return render(request, self.template_name, {
                    'form': form,
                    'error_message': 'Username e/o password errati!',
                })

        return render(request, self.template_name, {
            'form': form,
            'error_message': 'Dati non validi. Riprova.',
        })

    def _get_client_ip(self, request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')


def logout_view(request):
    """Logout user and redirect to login page."""
    if request.user.is_authenticated:
        emit_audit_event(request, "auth.logout", detail={})
    logout(request)
    return redirect(settings.LOGIN_URL)
