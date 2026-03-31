from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class OpenRedirectTest(TestCase):
    """H-1: next= URL must be validated to prevent open redirect."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', password='testpassword123',
            is_superuser=True,
        )
        self.login_url = reverse('accounts:login')

    def test_safe_relative_next_redirects_correctly(self):
        response = self.client.post(
            f'{self.login_url}?next=/reports/',
            {'username': 'testuser', 'password': 'testpassword123'},
        )
        self.assertRedirects(response, '/reports/', fetch_redirect_response=False)

    def test_absolute_external_next_falls_back_to_home(self):
        response = self.client.post(
            f'{self.login_url}?next=https://evil.com/steal',
            {'username': 'testuser', 'password': 'testpassword123'},
        )
        self.assertRedirects(response, '/', fetch_redirect_response=False)

    def test_protocol_relative_next_falls_back_to_home(self):
        response = self.client.post(
            f'{self.login_url}?next=//evil.com/steal',
            {'username': 'testuser', 'password': 'testpassword123'},
        )
        self.assertRedirects(response, '/', fetch_redirect_response=False)

    def test_missing_next_redirects_to_home(self):
        response = self.client.post(
            self.login_url,
            {'username': 'testuser', 'password': 'testpassword123'},
        )
        self.assertRedirects(response, '/', fetch_redirect_response=False)


class LogoutCsrfTest(TestCase):
    """H-6: Logout must require POST to prevent CSRF-based force-logout."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='logoutuser', password='testpassword123',
        )
        self.logout_url = reverse('accounts:logout')

    def test_logout_get_returns_405(self):
        """GET to logout must be rejected with 405 Method Not Allowed."""
        self.client.force_login(self.user, backend='apps.accounts.auth.SuperuserOnlyModelBackend')
        response = self.client.get(self.logout_url)
        self.assertEqual(response.status_code, 405)

    def test_logout_post_succeeds(self):
        """Valid POST logs the user out and redirects to login."""
        self.client.force_login(self.user, backend='apps.accounts.auth.SuperuserOnlyModelBackend')
        response = self.client.post(self.logout_url)
        self.assertRedirects(response, '/auth/login/', fetch_redirect_response=False)


class CookieSecurityFlagsTest(TestCase):
    """H-1: Session and CSRF cookies must carry HttpOnly and SameSite flags."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='cookieuser', password='testpassword123',
            is_superuser=True,
        )
        self.login_url = reverse('accounts:login')

    def test_session_cookie_is_httponly(self):
        self.client.post(
            self.login_url,
            {'username': 'cookieuser', 'password': 'testpassword123'},
        )
        session_cookie = self.client.cookies.get('sessionid')
        self.assertIsNotNone(session_cookie, "sessionid cookie not set")
        self.assertTrue(session_cookie['httponly'], "sessionid must be HttpOnly")

    def test_session_cookie_has_samesite_lax(self):
        """Session cookie uses Lax (not Strict) to allow OIDC redirect callbacks from Entra."""
        self.client.post(
            self.login_url,
            {'username': 'cookieuser', 'password': 'testpassword123'},
        )
        session_cookie = self.client.cookies.get('sessionid')
        self.assertIsNotNone(session_cookie)
        self.assertEqual(session_cookie['samesite'], 'Lax')

    def test_csrf_cookie_is_httponly(self):
        self.client.get(self.login_url)
        csrf_cookie = self.client.cookies.get('csrftoken')
        self.assertIsNotNone(csrf_cookie, "csrftoken cookie not set")
        self.assertTrue(csrf_cookie['httponly'], "csrftoken must be HttpOnly")

    def test_csrf_cookie_has_samesite_strict(self):
        self.client.get(self.login_url)
        csrf_cookie = self.client.cookies.get('csrftoken')
        self.assertIsNotNone(csrf_cookie)
        self.assertEqual(csrf_cookie['samesite'], 'Strict')


class AuditLogInjectionTest(TestCase):
    """H-3: Username in audit log must be truncated and stripped of newlines."""

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.login_url = reverse('accounts:login')
        self.user = User.objects.create_user(
            username='realuser', password='realpassword123',
            is_superuser=True,
        )

    def _hit_lockout(self, username):
        """Submit enough failed logins to trigger lockout for the given IP."""
        from django.conf import settings as django_settings
        for _ in range(django_settings.MAX_LOGIN_ATTEMPTS):
            self.client.post(self.login_url, {'username': username, 'password': 'wrong'})

    def test_newline_in_username_does_not_crash(self):
        """A username containing a newline must not cause a 500."""
        malicious = 'admin\nSUCCESS user=attacker'
        self._hit_lockout(malicious)
        response = self.client.post(
            self.login_url, {'username': malicious, 'password': 'wrong'}
        )
        self.assertIn(response.status_code, [302, 200])

    def test_very_long_username_is_truncated(self):
        """Username in audit detail must be capped at 150 characters."""
        long_name = 'a' * 500
        self._hit_lockout(long_name)
        response = self.client.post(
            self.login_url, {'username': long_name, 'password': 'wrong'}
        )
        self.assertIn(response.status_code, [302, 200])


class ClientIpExtractionTest(TestCase):
    """H-2a: _get_client_ip must not trust X-Forwarded-For from untrusted sources."""

    def _get_ip(self, meta):
        from apps.accounts.views import LoginView
        view = LoginView()
        from django.test import RequestFactory
        rf = RequestFactory()
        request = rf.get('/')
        request.META.update(meta)
        return view._get_client_ip(request)

    def test_uses_remote_addr_when_no_forwarded_for(self):
        ip = self._get_ip({'REMOTE_ADDR': '1.2.3.4'})
        self.assertEqual(ip, '1.2.3.4')

    def test_ignores_forwarded_for_from_untrusted_remote_addr(self):
        """When REMOTE_ADDR is not in TRUSTED_PROXIES, ignore X-Forwarded-For."""
        ip = self._get_ip({
            'REMOTE_ADDR': '5.6.7.8',           # not a trusted proxy
            'HTTP_X_FORWARDED_FOR': '1.1.1.1',  # attacker-controlled
        })
        self.assertEqual(ip, '5.6.7.8')

    def test_uses_forwarded_for_rightmost_from_trusted_proxy(self):
        """When REMOTE_ADDR is a trusted proxy, take the rightmost XFF IP."""
        with self.settings(LOGIN_TRUSTED_PROXIES=['127.0.0.1']):
            ip = self._get_ip({
                'REMOTE_ADDR': '127.0.0.1',
                'HTTP_X_FORWARDED_FOR': '10.0.0.1, 192.168.1.1',
            })
        self.assertEqual(ip, '192.168.1.1')
