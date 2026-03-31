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

    def test_non_hex_string_raises_value_error(self):
        """uuid.UUID rejects strings containing non-hex characters."""
        from apps.reports.services.report_data import _validate_report_id
        with self.assertRaises(ValueError):
            _validate_report_id('gggggggg-gggg-gggg-gggg-gggggggggggg')


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


class PaginationValidationTest(TestCase):
    """M-3: Pagination parameters must be validated before int() conversion."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='pageuser', password='testpassword123',
            is_superuser=True,
        )
        self.client.force_login(self.user, backend='apps.accounts.auth.SuperuserOnlyModelBackend')

    def test_non_numeric_page_returns_400(self):
        response = self.client.get('/api/data/', {'page': 'abc'})
        self.assertEqual(response.status_code, 400)

    def test_non_numeric_per_page_returns_400(self):
        response = self.client.get('/api/data/', {'per_page': 'xyz'})
        self.assertEqual(response.status_code, 400)

    def test_negative_page_is_clamped_to_1(self):
        """Negative page should not cause a negative offset — clamp to 1."""
        with patch('apps.reports.views.api.query_feature_layer', return_value={'features': []}):
            response = self.client.get('/api/data/', {'page': '-5'})
        self.assertIn(response.status_code, [200, 400])
        if response.status_code == 200:
            body = json.loads(response.content)
            self.assertGreaterEqual(body.get('page', 1), 1)


class ImageProxyValidationTest(TestCase):
    """M-1: Image proxy must reject negative integer parameters.

    Django's <int:> URL converter rejects negative values at routing level (404).
    The view also has an explicit >= 0 check as defense-in-depth.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username='imguser', password='testpassword123',
            is_superuser=True,
        )
        self.client.force_login(self.user, backend='apps.accounts.auth.SuperuserOnlyModelBackend')

    def test_negative_layer_rejected_by_url_router(self):
        """Django's <int:> converter rejects negative values before reaching the view."""
        response = self.client.get('/api/image/-1/1/1/')
        self.assertEqual(response.status_code, 404)

    def test_negative_object_id_rejected_by_url_router(self):
        response = self.client.get('/api/image/0/-1/1/')
        self.assertEqual(response.status_code, 404)

    def test_negative_attachment_id_rejected_by_url_router(self):
        response = self.client.get('/api/image/0/1/-1/')
        self.assertEqual(response.status_code, 404)


class FilterAllowlistTest(TestCase):
    """M-2: Filter regex must accept Italian accented characters."""

    def test_italian_accented_name_is_valid(self):
        from apps.reports.views.api import build_where_clause
        # Should not raise ValueError
        where = build_where_clause({'nome_operatore': ['Società Costruzioni']})
        self.assertIn('Societ', where)

    def test_accented_tratta_is_valid(self):
        from apps.reports.views.api import build_where_clause
        where = build_where_clause({'tratta': ['Nò-Milano']})
        self.assertIn('Nò-Milano', where)

    def test_sql_metacharacters_still_rejected(self):
        from apps.reports.views.api import build_where_clause
        with self.assertRaises(ValueError):
            build_where_clause({'nome_operatore': ["admin'; DROP TABLE"]})
