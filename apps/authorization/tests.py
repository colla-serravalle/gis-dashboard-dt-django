from django.contrib.auth.models import User, Group
from django.test import TestCase, Client
from django.urls import reverse

from apps.authorization.models import Service


class ServiceGetListUrlTest(TestCase):
    """Unit tests for Service.get_list_url property."""

    def test_returns_resolved_url_for_valid_url_name(self):
        service = Service(list_url_name="reports:report_list")
        url = service.get_list_url
        self.assertEqual(url, reverse("reports:report_list"))

    def test_returns_empty_string_for_blank_url_name(self):
        service = Service(list_url_name="")
        self.assertEqual(service.get_list_url, "")

    def test_returns_empty_string_for_invalid_url_name(self):
        service = Service(list_url_name="nonexistent:view")
        self.assertEqual(service.get_list_url, "")


class ServiceOrderingTest(TestCase):
    """Service queryset is ordered by display_order then name."""

    def test_ordering_by_display_order_then_name(self):
        Service.objects.create(name="Z Service", app_label="z_svc", display_order=2)
        Service.objects.create(name="A Service", app_label="a_svc", display_order=1)
        Service.objects.create(name="M Service", app_label="m_svc", display_order=1)
        names = list(Service.objects.values_list("name", flat=True))
        self.assertEqual(names, ["A Service", "M Service", "Z Service"])


class HomePageServiceVisibilityTest(TestCase):
    """Integration tests: home page only shows accessible services."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user("testuser", password="pass")

        # Groups
        self.dashboard_group = Group.objects.create(name="dashboard_users_test")
        self.reports_group = Group.objects.create(name="reports_users_test")
        self.user.groups.add(self.dashboard_group, self.reports_group)

        # core Service — required so ServiceAccessMiddleware allows home page access
        core_svc = Service.objects.create(
            name="Dashboard", app_label="core", is_active=True, display_order=0
        )
        core_svc.allowed_groups.set([self.dashboard_group])

        # Reports service — user has access
        reports_svc = Service.objects.create(
            name="Reports",
            app_label="reports",
            is_active=True,
            icon_class="fa-solid fa-file-invoice",
            list_url_name="reports:report_list",
            display_order=1,
        )
        reports_svc.allowed_groups.set([self.reports_group])

        # Segnalazioni service — user does NOT have access (no groups set)
        Service.objects.create(
            name="Segnalazioni",
            app_label="segnalazioni",
            is_active=True,
            icon_class="fa-solid fa-triangle-exclamation",
            list_url_name="segnalazioni:segnalazioni_list",
            display_order=2,
        )

        self.client.force_login(self.user)

    def test_user_sees_only_accessible_service_card(self):
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Reports")
        self.assertNotContains(response, "Segnalazioni")

    def test_superuser_sees_all_services(self):
        superuser = User.objects.create_superuser("admin_test", password="pass")
        self.client.force_login(superuser)
        response = self.client.get(reverse("core:home"))
        self.assertContains(response, "Reports")
        self.assertContains(response, "Segnalazioni")

    def test_user_with_no_services_sees_no_services_section(self):
        # Create a user with only dashboard access (no service cards)
        bare_user = User.objects.create_user("bare_user", password="pass")
        bare_user.groups.add(self.dashboard_group)
        self.client.force_login(bare_user)
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "grid-container columns-3")
