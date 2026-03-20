import json
import logging

from django.test import SimpleTestCase

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
