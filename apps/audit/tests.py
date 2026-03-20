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
