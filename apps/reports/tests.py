import json
from unittest.mock import patch

from django.test import TestCase
from django.contrib.auth import get_user_model

User = get_user_model()


class ReportIdValidationTest(TestCase):
    """H-4: _validate_report_id rejects non-GUID values."""

    def test_valid_guid_with_dashes_passes(self):
        from apps.reports.services.report_data import _validate_report_id
        _validate_report_id('a1b2c3d4-e5f6-7890-abcd-ef1234567890')

    def test_valid_guid_without_dashes_passes(self):
        from apps.reports.services.report_data import _validate_report_id
        _validate_report_id('a1b2c3d4e5f67890abcdef1234567890')

    def test_valid_guid_with_curly_braces_passes(self):
        from apps.reports.services.report_data import _validate_report_id
        _validate_report_id('{a1b2c3d4-e5f6-7890-abcd-ef1234567890}')

    def test_sql_injection_raises_value_error(self):
        from apps.reports.services.report_data import _validate_report_id
        with self.assertRaises(ValueError):
            _validate_report_id("' OR '1'='1")

    def test_empty_string_raises_value_error(self):
        from apps.reports.services.report_data import _validate_report_id
        with self.assertRaises(ValueError):
            _validate_report_id('')

    def test_none_raises_value_error(self):
        from apps.reports.services.report_data import _validate_report_id
        with self.assertRaises(ValueError):
            _validate_report_id(None)

    def test_path_traversal_raises_value_error(self):
        from apps.reports.services.report_data import _validate_report_id
        with self.assertRaises(ValueError):
            _validate_report_id('../../../etc/passwd')


class ReportDetailViewValidationTest(TestCase):
    """H-4: ReportDetailView returns 400 for invalid report IDs."""

    def setUp(self):
        # MUST be superuser — ServiceAccessMiddleware denies non-superusers
        # when no Service DB record exists (test DB has none).
        self.user = User.objects.create_user(
            username='reportuser', password='testpassword123',
            is_superuser=True,
        )
        # Use SuperuserOnlyModelBackend (registered in AUTHENTICATION_BACKENDS)
        # so that force_login sets a valid backend in the session.
        # This prevents both the OIDC SessionRefresh redirect (not an
        # OIDCAuthenticationBackend subclass) and the login_required redirect.
        self.client.force_login(
            self.user,
            backend='apps.accounts.auth.SuperuserOnlyModelBackend',
        )

    def test_invalid_report_id_returns_400(self):
        response = self.client.get("/reports/detail/?id=' OR 1=1 --")
        self.assertEqual(response.status_code, 400)

    def test_missing_report_id_redirects(self):
        response = self.client.get('/reports/detail/')
        self.assertEqual(response.status_code, 302)


class PdfExportViewValidationTest(TestCase):
    """H-4: PDF export endpoint returns 400 for invalid report IDs."""

    def setUp(self):
        # MUST be superuser to bypass ServiceAccessMiddleware
        self.user = User.objects.create_user(
            username='pdfuser', password='testpassword123',
            is_superuser=True,
        )
        self.client.force_login(self.user, backend='apps.accounts.auth.SuperuserOnlyModelBackend')

    def test_invalid_rowid_returns_400(self):
        response = self.client.get("/reports/pdf/?rowid=' OR 1=1 --")
        self.assertEqual(response.status_code, 400)

    def test_missing_rowid_returns_400(self):
        response = self.client.get('/reports/pdf/')
        self.assertEqual(response.status_code, 400)


class ExceptionSanitizationTest(TestCase):
    """H-5: Raw exception messages must not be returned to API clients."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='apiuser', password='testpassword123',
            is_superuser=True,
        )
        self.client.force_login(self.user, backend='apps.accounts.auth.SuperuserOnlyModelBackend')

    def test_get_data_500_returns_generic_message(self):
        with patch('apps.reports.views.api.query_feature_layer', side_effect=RuntimeError('secret connection string')):
            response = self.client.get('/api/data/')
        self.assertEqual(response.status_code, 500)
        body = json.loads(response.content)
        self.assertNotIn('secret connection string', body.get('error', ''))

    def test_get_filter_options_500_returns_generic_message(self):
        with patch('apps.reports.views.api.query_feature_layer', side_effect=RuntimeError('secret connection string')):
            response = self.client.get('/api/filters/')
        self.assertEqual(response.status_code, 500)
        body = json.loads(response.content)
        self.assertNotIn('secret connection string', body.get('error', ''))

    def test_image_proxy_500_returns_generic_message(self):
        with patch('apps.reports.views.api.get_arcgis_service', side_effect=RuntimeError('secret arcgis token')):
            response = self.client.get('/api/image/0/1/1/')
        self.assertEqual(response.status_code, 500)
        self.assertNotIn(b'secret arcgis token', response.content)
