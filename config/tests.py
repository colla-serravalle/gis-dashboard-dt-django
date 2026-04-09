from django.test import TestCase, RequestFactory, override_settings
from config.strings import UI_STRINGS
from config.context_processors import ui_strings as ui_strings_processor


class UIStringsTest(TestCase):
    """Verifica che UI_STRINGS contenga le chiavi attese."""

    def test_all_values_are_strings(self):
        for key, value in UI_STRINGS.items():
            with self.subTest(key=key):
                self.assertIsInstance(value, str, f"UI_STRINGS['{key}'] non è una stringa")

    def test_required_keys_present(self):
        required_keys = [
            # Comuni
            "loading", "actions_col", "error_title",
            # Nav
            "nav_home", "nav_documents", "nav_services",
            "nav_contacts", "nav_support", "nav_profile",
            "nav_logout", "nav_toggle_title",
            # Home
            "home_greeting", "home_welcome",
            "home_services_title", "home_services_subtitle", "home_goto_btn",
            # Login
            "login_title", "login_azure_btn", "login_divider",
            "login_admin_only", "login_username_label",
            "login_password_label", "login_submit_btn",
            # Reports
            "reports_page_title", "reports_page_subtitle",
            "reports_back_link", "reports_detail_prefix",
            "reports_pdf_btn", "reports_maps_btn", "reports_pdf_loading",
            # Segnalazioni
            "segnalazioni_page_title", "segnalazioni_page_subtitle",
            "segnalazioni_col_title", "segnalazioni_col_category",
            "segnalazioni_col_status", "segnalazioni_col_date",
            # Profilo
            "profile_page_title", "profile_field_username",
            "profile_field_email", "profile_field_fullname",
            "profile_field_joined",
        ]
        for key in required_keys:
            with self.subTest(key=key):
                self.assertIn(key, UI_STRINGS)

    def test_no_empty_values(self):
        for key, value in UI_STRINGS.items():
            with self.subTest(key=key):
                self.assertTrue(value.strip(), f"UI_STRINGS['{key}'] è vuoto o solo spazi")


class UIStringsContextProcessorTest(TestCase):
    """Verifica che il context processor inietti ui_strings."""

    def setUp(self):
        self.factory = RequestFactory()

    def test_returns_ui_strings_dict(self):
        request = self.factory.get('/')
        result = ui_strings_processor(request)
        self.assertIn("ui_strings", result)
        self.assertIs(result["ui_strings"], UI_STRINGS)


@override_settings(
    MIDDLEWARE=[
        'django.middleware.security.SecurityMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.common.CommonMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        # Disable OIDC SessionRefresh for this test
        'apps.authorization.middleware.ServiceAccessMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
        'django.middleware.clickjacking.XFrameOptionsMiddleware',
        'config.middleware.ContentSecurityPolicyMiddleware',
    ]
)
class UIStringsInTemplateContextTest(TestCase):
    """Verifica che ui_strings sia disponibile nel context dei template via HTTP."""

    def setUp(self):
        from django.contrib.auth.models import User, Group
        from apps.authorization.models import Service

        self.user = User.objects.create_user("testuser_ctx", password="pass")
        group = Group.objects.create(name="core_group_ctx")
        self.user.groups.add(group)
        core_svc = Service.objects.create(
            name="Dashboard", app_label="core", is_active=True, display_order=0
        )
        core_svc.allowed_groups.set([group])
        self.client.force_login(self.user)

    def test_ui_strings_in_home_context(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn("ui_strings", response.context)

    def test_home_renders_greeting_from_ui_strings(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Buongiorno")
