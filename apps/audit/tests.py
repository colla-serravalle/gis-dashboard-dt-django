import json
import logging

from django.test import SimpleTestCase, TestCase

from apps.audit.formatters import NIS2JsonFormatter


def _make_record(level=logging.INFO, **extra):
    """Helper: create a LogRecord with arbitrary extra fields."""
    record = logging.LogRecord(
        name="audit", level=level,
        pathname="", lineno=0, msg="test-event", args=(), exc_info=None,
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return record


class AppJsonFormatterTest(TestCase):

    def _make_record(self, name="apps.core.services.arcgis", msg="test message"):
        logger = logging.getLogger(name)
        record = logger.makeRecord(
            name=name, level=logging.INFO, fn="", lno=0,
            msg=msg, args=(), exc_info=None,
        )
        return record

    def test_format_returns_valid_json(self):
        from apps.audit.formatters import AppJsonFormatter
        fmt = AppJsonFormatter()
        output = fmt.format(self._make_record())
        data = json.loads(output)
        self.assertIsInstance(data, dict)

    def test_format_contains_required_fields(self):
        from apps.audit.formatters import AppJsonFormatter
        fmt = AppJsonFormatter()
        data = json.loads(fmt.format(self._make_record()))
        for field in ("timestamp", "level", "app", "message"):
            self.assertIn(field, data)

    def test_app_field_equals_logger_name(self):
        from apps.audit.formatters import AppJsonFormatter
        fmt = AppJsonFormatter()
        data = json.loads(fmt.format(self._make_record(name="apps.reports.views.api")))
        self.assertEqual(data["app"], "apps.reports.views.api")

    def test_message_field_equals_log_message(self):
        from apps.audit.formatters import AppJsonFormatter
        fmt = AppJsonFormatter()
        data = json.loads(fmt.format(self._make_record(msg="hello world")))
        self.assertEqual(data["message"], "hello world")

    def test_timestamp_is_iso8601_with_utc_offset(self):
        from apps.audit.formatters import AppJsonFormatter
        fmt = AppJsonFormatter()
        data = json.loads(fmt.format(self._make_record()))
        # Matches e.g. 2026-03-24T10:23:00.123456+01:00
        self.assertRegex(data["timestamp"], r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.*[+-]\d{2}:\d{2}")

    def test_now_returns_iso8601_with_utc_offset(self):
        from apps.audit.formatters import AppJsonFormatter
        fmt = AppJsonFormatter()
        ts = fmt._now()
        self.assertRegex(ts, r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.*[+-]\d{2}:\d{2}")


class NIS2FormatterInheritanceTest(TestCase):

    def test_nis2_is_subclass_of_app_formatter(self):
        from apps.audit.formatters import AppJsonFormatter, NIS2JsonFormatter
        self.assertTrue(issubclass(NIS2JsonFormatter, AppJsonFormatter))

    def test_nis2_does_not_override_now(self):
        from apps.audit.formatters import AppJsonFormatter, NIS2JsonFormatter
        # _now() must be inherited, not overridden
        self.assertNotIn("_now", NIS2JsonFormatter.__dict__)

    def test_nis2_output_excludes_message_and_app(self):
        from apps.audit.formatters import NIS2JsonFormatter
        logger = logging.getLogger("audit")
        record = logger.makeRecord(
            name="audit", level=logging.INFO, fn="", lno=0,
            msg="auth.login.success", args=(), exc_info=None,
        )
        record.event_type = "auth.login.success"
        record.user = "mario"
        record.ip = "127.0.0.1"
        record.session_id = "abc"
        record.path = "/login/"
        record.method = "POST"
        record.detail = {}
        fmt = NIS2JsonFormatter()
        data = json.loads(fmt.format(record))
        self.assertNotIn("message", data)
        self.assertNotIn("app", data)


class NIS2JsonFormatterTest(SimpleTestCase):

    def setUp(self):
        self.formatter = NIS2JsonFormatter()
        self.base_extra = {
            "event_type": "auth.login.success",
            "user": "mario.rossi",
            "ip": "10.0.0.1",
            "session_id": "abc123",
            "path": "/auth/login/",
            "method": "POST",
            "detail": {"auth_method": "local"},
        }

    def _format(self, **extra):
        fields = {**self.base_extra, **extra}
        return json.loads(self.formatter.format(_make_record(**fields)))

    def test_output_is_valid_json(self):
        output = self.formatter.format(_make_record(**self.base_extra))
        parsed = json.loads(output)
        self.assertIsInstance(parsed, dict)

    def test_all_required_fields_present(self):
        parsed = self._format()
        for field in ("timestamp", "level", "event_type", "session_id",
                      "user", "ip", "path", "method", "detail"):
            self.assertIn(field, parsed)

    def test_timestamp_is_iso8601_with_offset(self):
        parsed = self._format()
        import re
        self.assertRegex(
            parsed["timestamp"],
            r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}",
        )
        self.assertRegex(parsed["timestamp"], r"[+-]\d{2}:\d{2}$")

    def test_level_field_matches_log_level(self):
        parsed = self._format()
        self.assertEqual(parsed["level"], "INFO")

        warn_parsed = json.loads(
            self.formatter.format(_make_record(level=logging.WARNING, **self.base_extra))
        )
        self.assertEqual(warn_parsed["level"], "WARNING")

    def test_session_id_can_be_null(self):
        parsed = self._format(session_id=None)
        self.assertIsNone(parsed["session_id"])

    def test_detail_is_always_an_object(self):
        parsed = self._format(detail={})
        self.assertIsInstance(parsed["detail"], dict)

    def test_missing_extra_fields_do_not_raise(self):
        """Formatter must not raise if extra fields are absent."""
        bare_record = logging.LogRecord(
            name="audit", level=logging.INFO,
            pathname="", lineno=0, msg="bare", args=(), exc_info=None,
        )
        output = self.formatter.format(bare_record)
        parsed = json.loads(output)
        self.assertIn("timestamp", parsed)


from unittest.mock import MagicMock

from django.test import RequestFactory

from apps.audit.utils import emit_audit_event, WARNING_EVENT_TYPES


def _make_request(username=None, session_key="sess-abc", path="/test/",
                  method="GET", remote_addr="10.0.0.1", forwarded_for=None):
    """Helper: build a minimal fake HttpRequest."""
    factory = RequestFactory()
    request = factory.generic(method, path)
    request.META["REMOTE_ADDR"] = remote_addr
    if forwarded_for:
        request.META["HTTP_X_FORWARDED_FOR"] = forwarded_for

    mock_user = MagicMock()
    if username:
        mock_user.is_authenticated = True
        mock_user.username = username
    else:
        mock_user.is_authenticated = False

    request.user = mock_user
    request.session = MagicMock()
    request.session.session_key = session_key
    return request


class EmitAuditEventTest(SimpleTestCase):

    def test_emits_info_for_normal_event(self):
        request = _make_request(username="mario")
        with self.assertLogs("audit", level="INFO") as cm:
            emit_audit_event(request, "auth.login.success", detail={"auth_method": "local"})
        self.assertEqual(len(cm.records), 1)
        self.assertEqual(cm.records[0].levelno, logging.INFO)

    def test_emits_warning_for_warning_event_types(self):
        request = _make_request(username="mario")
        for event_type in WARNING_EVENT_TYPES:
            with self.assertLogs("audit", level="WARNING") as cm:
                emit_audit_event(request, event_type, detail={})
            self.assertEqual(cm.records[0].levelno, logging.WARNING)

    def test_extracts_username_from_authenticated_user(self):
        request = _make_request(username="mario.rossi")
        with self.assertLogs("audit", level="INFO") as cm:
            emit_audit_event(request, "auth.login.success", detail={})
        self.assertEqual(cm.records[0].user, "mario.rossi")

    def test_anonymous_user_yields_anonymous_string(self):
        request = _make_request()  # no username → not authenticated
        with self.assertLogs("audit", level="INFO") as cm:
            emit_audit_event(request, "auth.logout", detail={})
        self.assertEqual(cm.records[0].user, "anonymous")

    def test_extracts_session_key(self):
        request = _make_request(username="u", session_key="my-session")
        with self.assertLogs("audit", level="INFO") as cm:
            emit_audit_event(request, "auth.logout", detail={})
        self.assertEqual(cm.records[0].session_id, "my-session")

    def test_null_session_key_when_no_session(self):
        request = _make_request(username="u", session_key=None)
        with self.assertLogs("audit", level="INFO") as cm:
            emit_audit_event(request, "auth.logout", detail={})
        self.assertIsNone(cm.records[0].session_id)

    def test_ip_from_remote_addr(self):
        request = _make_request(username="u", remote_addr="192.168.1.5")
        with self.assertLogs("audit", level="INFO") as cm:
            emit_audit_event(request, "auth.logout", detail={})
        self.assertEqual(cm.records[0].ip, "192.168.1.5")

    def test_ip_from_x_forwarded_for_first_value(self):
        request = _make_request(username="u", forwarded_for="203.0.113.1, 10.0.0.1")
        with self.assertLogs("audit", level="INFO") as cm:
            emit_audit_event(request, "auth.logout", detail={})
        self.assertEqual(cm.records[0].ip, "203.0.113.1")

    def test_path_is_request_path(self):
        request = _make_request(username="u", path="/reports/list/")
        with self.assertLogs("audit", level="INFO") as cm:
            emit_audit_event(request, "data.report.viewed", detail={})
        self.assertEqual(cm.records[0].path, "/reports/list/")

    def test_detail_defaults_to_empty_dict(self):
        request = _make_request(username="u")
        with self.assertLogs("audit", level="INFO") as cm:
            emit_audit_event(request, "auth.logout")
        self.assertEqual(cm.records[0].detail, {})

    def test_event_type_constant_namespace(self):
        """All WARNING event types follow dotted namespace convention."""
        for et in WARNING_EVENT_TYPES:
            parts = et.split(".")
            self.assertGreaterEqual(len(parts), 2, msg=f"Bad event type: {et}")


from django.contrib.auth.models import Group, User
from django.test import override_settings
from django.urls import reverse

# Minimal middleware stack for integration tests — strips OIDC SessionRefresh
# and ServiceAccessMiddleware to keep tests focused on auth events only.
_TEST_MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


@override_settings(
    MIDDLEWARE=_TEST_MIDDLEWARE,
    AUTHENTICATION_BACKENDS=["django.contrib.auth.backends.ModelBackend"],
)
class AuthEventTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user("testuser", password="correct-password")

    def test_login_success_emits_auth_login_success(self):
        with self.assertLogs("audit", level="INFO") as cm:
            self.client.post(reverse("accounts:login"), {
                "username": "testuser",
                "password": "correct-password",
            })
        event_types = [r.event_type for r in cm.records]
        self.assertIn("auth.login.success", event_types)

    def test_login_success_detail_contains_auth_method(self):
        with self.assertLogs("audit", level="INFO") as cm:
            self.client.post(reverse("accounts:login"), {
                "username": "testuser",
                "password": "correct-password",
            })
        record = next(r for r in cm.records if r.event_type == "auth.login.success")
        self.assertIn("auth_method", record.detail)

    def test_login_failure_emits_auth_login_failure(self):
        with self.assertLogs("audit", level="WARNING") as cm:
            self.client.post(reverse("accounts:login"), {
                "username": "testuser",
                "password": "wrong-password",
            })
        event_types = [r.event_type for r in cm.records]
        self.assertIn("auth.login.failure", event_types)

    def test_login_failure_detail_contains_attempt_count(self):
        with self.assertLogs("audit", level="WARNING") as cm:
            self.client.post(reverse("accounts:login"), {
                "username": "testuser",
                "password": "wrong-password",
            })
        record = next(r for r in cm.records if r.event_type == "auth.login.failure")
        self.assertIn("attempt_count", record.detail)

    def test_logout_emits_auth_logout(self):
        self.client.force_login(self.user)
        with self.assertLogs("audit", level="INFO") as cm:
            self.client.get(reverse("accounts:logout"))
        event_types = [r.event_type for r in cm.records]
        self.assertIn("auth.logout", event_types)

    def test_lockout_emits_auth_login_locked(self):
        session = self.client.session
        session["login_attempts"] = 10
        session["last_attempt"] = 9999999999  # far future — always locked
        session.save()
        with self.assertLogs("audit", level="WARNING") as cm:
            self.client.post(reverse("accounts:login"), {
                "username": "testuser",
                "password": "any",
            })
        event_types = [r.event_type for r in cm.records]
        self.assertIn("auth.login.locked", event_types)

    def test_lockout_detail_contains_attempt_count_and_locked_until(self):
        import time
        session = self.client.session
        session["login_attempts"] = 10
        session["last_attempt"] = time.time()
        session.save()
        with self.assertLogs("audit", level="WARNING") as cm:
            self.client.post(reverse("accounts:login"), {
                "username": "testuser",
                "password": "any",
            })
        record = next(r for r in cm.records if r.event_type == "auth.login.locked")
        self.assertIn("attempt_count", record.detail)
        self.assertIn("locked_until", record.detail)


from unittest.mock import patch, MagicMock

from apps.accounts.auth import AzureOIDCBackend


class UserCreatedEventTest(SimpleTestCase):

    def test_create_user_emits_auth_user_created(self):
        backend = AzureOIDCBackend()
        mock_request = MagicMock()
        mock_request.user = MagicMock(is_authenticated=False)
        mock_request.session = MagicMock(session_key="sess-xyz")
        mock_request.META = {"REMOTE_ADDR": "10.0.0.1"}
        mock_request.path = "/oidc/callback/"
        mock_request.method = "GET"
        backend.request = mock_request

        claims = {
            "email": "new.user@example.com",
            "given_name": "New",
            "family_name": "User",
        }

        with patch.object(backend.UserModel.objects, "create_user") as mock_create, \
             patch.object(backend, "sync_user"), \
             self.assertLogs("audit", level="INFO") as cm:
            mock_create.return_value = MagicMock(email="new.user@example.com")
            backend.create_user(claims)

        event_types = [r.event_type for r in cm.records]
        self.assertIn("auth.user.created", event_types)

    def test_create_user_detail_contains_email(self):
        backend = AzureOIDCBackend()
        mock_request = MagicMock()
        mock_request.user = MagicMock(is_authenticated=False)
        mock_request.session = MagicMock(session_key="sess-xyz")
        mock_request.META = {"REMOTE_ADDR": "10.0.0.1"}
        mock_request.path = "/oidc/callback/"
        mock_request.method = "GET"
        backend.request = mock_request

        claims = {"email": "new.user@example.com", "given_name": "New", "family_name": "User"}

        with patch.object(backend.UserModel.objects, "create_user") as mock_create, \
             patch.object(backend, "sync_user"), \
             self.assertLogs("audit", level="INFO") as cm:
            mock_create.return_value = MagicMock(email="new.user@example.com")
            backend.create_user(claims)

        record = next(r for r in cm.records if r.event_type == "auth.user.created")
        self.assertEqual(record.detail["email"], "new.user@example.com")


# Minimal middleware stack for authorization tests — includes ServiceAccessMiddleware
_AUTHZ_MIDDLEWARE = _TEST_MIDDLEWARE + ["apps.authorization.middleware.ServiceAccessMiddleware"]


from apps.authorization.models import Service


@override_settings(
    MIDDLEWARE=_AUTHZ_MIDDLEWARE,
    AUTHENTICATION_BACKENDS=["django.contrib.auth.backends.ModelBackend"],
)
class AuthzDeniedEventTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user("authz_testuser", password="password")

    def test_access_denied_service_not_found(self):
        """Test authz.access.denied event when service record does not exist."""
        self.client.force_login(self.user)

        # Make a GET request to /reports/ which maps to 'reports' app_label
        # and has no Service record. Since DEFAULT_POLICY is "deny", this should
        # trigger authz.access.denied with reason="service_not_found"
        response = self.client.get("/reports/")

        # Check that the response is 403 Forbidden before checking logs
        self.assertEqual(response.status_code, 403)

        # Now verify the audit event was emitted by making another request
        # inside the assertLogs context
        with self.assertLogs("audit", level="WARNING") as cm:
            self.client.get("/reports/")

        # Check that authz.access.denied event was emitted
        records = [r for r in cm.records if r.event_type == "authz.access.denied"]
        self.assertTrue(records, "No authz.access.denied event was emitted")
        record = records[0]
        self.assertEqual(record.detail["app_label"], "reports")
        self.assertEqual(record.detail["reason"], "service_not_found")

    def test_access_denied_group_not_permitted(self):
        """Test authz.access.denied event when user lacks group access to service."""
        self.client.force_login(self.user)

        # Create a Service record for 'segnalazioni' app with no allowed_groups
        service = Service.objects.create(
            name="Segnalazioni",
            app_label="segnalazioni",
            is_active=True,
        )

        # Make a GET request to /segnalazioni/ which maps to 'segnalazioni' app_label
        # User has no groups, so service.user_has_access() returns False
        response = self.client.get("/segnalazioni/")

        # Check that the response is 403 Forbidden before checking logs
        self.assertEqual(response.status_code, 403)

        # Now verify the audit event was emitted by making another request
        # inside the assertLogs context
        with self.assertLogs("audit", level="WARNING") as cm:
            self.client.get("/segnalazioni/")

        # Check that authz.access.denied event was emitted
        records = [r for r in cm.records if r.event_type == "authz.access.denied"]
        self.assertTrue(records, "No authz.access.denied event was emitted")
        record = records[0]
        self.assertEqual(record.detail["app_label"], "segnalazioni")
        self.assertEqual(record.detail["reason"], "group_not_permitted")


class GroupChangedSignalTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user("groupuser", password="pass")
        self.group_a = Group.objects.create(name="group_a")
        self.group_b = Group.objects.create(name="group_b")

    def test_adding_group_emits_authz_group_changed(self):
        with self.assertLogs("audit", level="INFO") as cm:
            self.user.groups.add(self.group_a)
        event_types = [r.event_type for r in cm.records]
        self.assertIn("authz.group.changed", event_types)

    def test_added_groups_in_detail(self):
        with self.assertLogs("audit", level="INFO") as cm:
            self.user.groups.add(self.group_a)
        record = next(r for r in cm.records if r.event_type == "authz.group.changed")
        self.assertIn("group_a", record.detail["groups_added"])

    def test_removing_group_emits_authz_group_changed(self):
        self.user.groups.add(self.group_a)
        with self.assertLogs("audit", level="INFO") as cm:
            with self.captureOnCommitCallbacks(execute=True):
                self.user.groups.remove(self.group_a)
        event_types = [r.event_type for r in cm.records]
        self.assertIn("authz.group.changed", event_types)

    def test_no_op_sync_does_not_emit(self):
        """Remove group_a then add it back — net zero change should not emit."""
        self.user.groups.add(self.group_a)

        with self.assertNoLogs("audit", level="INFO"):
            with self.captureOnCommitCallbacks(execute=True):
                self.user.groups.remove(self.group_a)
                self.user.groups.add(self.group_a)


@override_settings(MIDDLEWARE=_TEST_MIDDLEWARE)
class AdminUserChangedEventTest(TestCase):

    def setUp(self):
        self.admin = User.objects.create_superuser("admin", password="admin-pass")
        self.target = User.objects.create_user("target_user", password="pass",
                                               first_name="Old")
        self.client.force_login(self.admin)
        self.change_url = f"/admin/auth/user/{self.target.pk}/change/"
        self.change_payload = {
            "username": self.target.username,
            "first_name": "New",
            "last_name": self.target.last_name,
            "email": self.target.email,
            "is_active": "on",
            "date_joined_0": "2024-01-01",
            "date_joined_1": "00:00:00",
            "_save": "Save",
        }

    def test_admin_user_save_emits_admin_user_changed(self):
        with self.assertLogs("audit", level="INFO") as cm:
            self.client.post(self.change_url, self.change_payload)
        event_types = [r.event_type for r in cm.records]
        self.assertIn("admin.user.changed", event_types)

    def test_admin_user_changed_detail_contains_changed_by(self):
        with self.assertLogs("audit", level="INFO") as cm:
            self.client.post(self.change_url, self.change_payload)
        record = next(r for r in cm.records if r.event_type == "admin.user.changed")
        self.assertEqual(record.detail["changed_by"], "admin")
        self.assertEqual(record.detail["user_changed"], "target_user")

    def test_admin_user_changed_detail_contains_fields(self):
        with self.assertLogs("audit", level="INFO") as cm:
            self.client.post(self.change_url, self.change_payload)
        record = next(r for r in cm.records if r.event_type == "admin.user.changed")
        self.assertIn("fields", record.detail)
        self.assertIn("first_name", record.detail["fields"])


@override_settings(MIDDLEWARE=_TEST_MIDDLEWARE + [
    "apps.authorization.middleware.ServiceAccessMiddleware",
])
class ReportDataAccessEventTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user("reportuser", password="pass")
        group = Group.objects.create(name="reports_group")
        self.user.groups.add(group)

        # Grant access to core and reports services
        core_svc = Service.objects.create(name="Core", app_label="core", is_active=True)
        core_svc.allowed_groups.set([group])
        reports_svc = Service.objects.create(name="Reports", app_label="reports", is_active=True)
        reports_svc.allowed_groups.set([group])

        self.client.force_login(self.user)

    def test_report_list_view_emits_data_report_viewed(self):
        with self.assertLogs("audit", level="INFO") as cm:
            self.client.get(reverse("reports:report_list"))
        event_types = [r.event_type for r in cm.records]
        self.assertIn("data.report.viewed", event_types)
        record = next(r for r in cm.records if r.event_type == "data.report.viewed")
        self.assertIsNone(record.detail.get("report_id"))

    def test_pdf_export_emits_data_report_exported(self):
        from unittest.mock import patch, MagicMock
        fake_data = {
            "raw_attributes": {"globalid": "{ABC}", "nome_operatore": ""},
            "object_id": 1,
            "report_id": "{TEST-ID}",
            "signature_attachments": [],
            "photos": [],
            "main_data": [],
            "location_data": [],
            "pk_pav_data": [],
            "pk_pav_headers": [],
            "impresa_data": [],
            "impresa_headers": [],
        }
        with patch("apps.reports.views.pdf.get_report_data", return_value=fake_data), \
             patch("apps.reports.views.pdf.pisa") as mock_pisa, \
             patch("apps.reports.views.pdf.local_image_to_base64_uri", return_value=""), \
             self.assertLogs("audit", level="INFO") as cm:
            mock_pisa.CreatePDF.return_value = 0
            self.client.get(reverse("reports:report_pdf") + "?rowid=TEST-ID")
        event_types = [r.event_type for r in cm.records]
        self.assertIn("data.report.exported", event_types)
        record = next(r for r in cm.records if r.event_type == "data.report.exported")
        self.assertIn("report_id", record.detail)


@override_settings(
    MIDDLEWARE=_TEST_MIDDLEWARE + ["apps.authorization.middleware.ServiceAccessMiddleware"],
)
class ArcGISQueryEventTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user("arcgisuser", password="pass")
        group = Group.objects.create(name="arcgis_group")
        self.user.groups.add(group)

        core_svc = Service.objects.create(name="Core", app_label="core", is_active=True)
        core_svc.allowed_groups.set([group])
        reports_svc = Service.objects.create(name="Reports", app_label="reports", is_active=True)
        reports_svc.allowed_groups.set([group])
        reports_api_svc = Service.objects.create(name="Reports API", app_label="reports_api", is_active=True)
        reports_api_svc.allowed_groups.set([group])

        self.client.force_login(self.user)

    def test_get_data_emits_data_arcgis_queried(self):
        fake_result = {"features": [{"attributes": {}}]}
        with patch("apps.reports.views.api.query_feature_layer", return_value=fake_result), \
             self.assertLogs("audit", level="INFO") as cm:
            self.client.get("/api/data/")
        event_types = [r.event_type for r in cm.records]
        self.assertIn("data.arcgis.queried", event_types)

    def test_arcgis_queried_detail_contains_record_count(self):
        fake_result = {"features": [{"attributes": {}}, {"attributes": {}}]}
        with patch("apps.reports.views.api.query_feature_layer", return_value=fake_result), \
             self.assertLogs("audit", level="INFO") as cm:
            self.client.get("/api/data/")
        record = next(r for r in cm.records if r.event_type == "data.arcgis.queried")
        self.assertEqual(record.detail["record_count"], 2)


@override_settings(MIDDLEWARE=_TEST_MIDDLEWARE + [
    "apps.authorization.middleware.ServiceAccessMiddleware",
])
class SegnalazioneDataAccessEventTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user("segnalazioniuser", password="pass")
        group = Group.objects.create(name="segn_group")
        self.user.groups.add(group)

        core_svc = Service.objects.create(name="Core", app_label="core", is_active=True)
        core_svc.allowed_groups.set([group])
        segn_svc = Service.objects.create(
            name="Segnalazioni", app_label="segnalazioni", is_active=True
        )
        segn_svc.allowed_groups.set([group])

        self.client.force_login(self.user)

    def test_segnalazioni_list_emits_data_segnalazione_viewed(self):
        with self.assertLogs("audit", level="INFO") as cm:
            self.client.get(reverse("segnalazioni:segnalazioni_list"))
        event_types = [r.event_type for r in cm.records]
        self.assertIn("data.segnalazione.viewed", event_types)
