"""Authentication views."""

import logging
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.core.cache import cache
from django.utils.http import url_has_allowed_host_and_scheme
from django.conf import settings
from django.views import View
from django.views.decorators.http import require_POST

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

        # Validate next_url here so the template never renders an unvalidated redirect
        raw_next = request.GET.get('next', '')
        next_url = raw_next if url_has_allowed_host_and_scheme(
            url=raw_next,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ) else ''

        return render(request, self.template_name, {
            'form': form,
            'error_message': error_message,
            'next_url': next_url,
        })

    def post(self, request):
        """Process login form submission."""
        form = LoginForm(request.POST)

        # IP-based rate limiting — not bypassable by clearing cookies
        client_ip = self._get_client_ip(request)
        cache_key = f'login_attempts_{client_ip}'
        max_attempts = getattr(settings, 'MAX_LOGIN_ATTEMPTS', 5)
        lockout_duration = getattr(settings, 'LOCKOUT_DURATION', 900)

        login_attempts = cache.get(cache_key, 0)

        if login_attempts >= max_attempts:
            raw_username = request.POST.get("username", "")
            safe_username = raw_username.replace('\n', ' ').replace('\r', ' ')[:150]
            emit_audit_event(request, "auth.login.locked", detail={
                "username_attempted": safe_username,
                "attempt_count": login_attempts,
                "ip": client_ip,
            })
            return redirect('/auth/login/?error=locked')

        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = authenticate(request, username=username, password=password)

            if user is not None:
                # Login successful — clear IP-based counter
                cache.delete(cache_key)
                login(request, user)

                emit_audit_event(request, "auth.login.success", detail={"auth_method": "local"})

                # Redirect to next URL or home — reject cross-host redirects
                next_url = request.GET.get('next', '/')
                if not url_has_allowed_host_and_scheme(
                    url=next_url,
                    allowed_hosts={request.get_host()},
                    require_https=request.is_secure(),
                ):
                    next_url = '/'
                return redirect(next_url)
            else:
                # Login failed — increment IP-based counter with TTL equal to lockout window
                new_count = login_attempts + 1
                cache.set(cache_key, new_count, timeout=lockout_duration)

                emit_audit_event(request, "auth.login.failure", detail={
                    "username_attempted": username,
                    "attempt_count": new_count,
                    "ip": client_ip,
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
        """Get client IP address from request.

        Only trusts X-Forwarded-For when REMOTE_ADDR is in LOGIN_TRUSTED_PROXIES.
        Takes the rightmost XFF entry to avoid attacker-prepended spoofed IPs.
        """
        remote_addr = request.META.get('REMOTE_ADDR', '')
        trusted_proxies = getattr(settings, 'LOGIN_TRUSTED_PROXIES', [])
        if remote_addr in trusted_proxies:
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
            if x_forwarded_for:
                return x_forwarded_for.split(',')[-1].strip()
        return remote_addr


@require_POST
def logout_view(request):
    """Logout user and redirect to login page. Requires POST to prevent CSRF-based force-logout."""
    if request.user.is_authenticated:
        emit_audit_event(request, "auth.logout", detail={})
    logout(request)
    return redirect(settings.LOGIN_URL)
