from django.test import TestCase
from django.contrib.auth import get_user_model

User = get_user_model()


class ContentSecurityPolicyTest(TestCase):
    """M-1: Every response must carry a Content-Security-Policy header."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='cspuser', password='testpassword123',
            is_superuser=True,
        )
        self.client.force_login(self.user, backend='apps.accounts.auth.SuperuserOnlyModelBackend')

    def test_csp_header_present_on_html_response(self):
        response = self.client.get('/')
        self.assertIn('Content-Security-Policy', response)

    def test_csp_default_src_is_self(self):
        response = self.client.get('/')
        csp = response.get('Content-Security-Policy', '')
        self.assertIn("default-src 'self'", csp)

    def test_csp_frame_ancestors_is_none(self):
        response = self.client.get('/')
        csp = response.get('Content-Security-Policy', '')
        self.assertIn("frame-ancestors 'none'", csp)
