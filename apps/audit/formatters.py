import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo


class AppJsonFormatter(logging.Formatter):
    """JSON formatter for operational app logs. Emits {timestamp, level, app, message}."""

    TZ = ZoneInfo("Europe/Rome")

    def _now(self) -> str:
        """ISO 8601 timestamp with Europe/Rome UTC offset."""
        return datetime.now(tz=self.TZ).isoformat()

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "timestamp": self._now(),
            "level": record.levelname,
            "app": record.name,
            "message": record.getMessage(),
        }
        return json.dumps(entry, ensure_ascii=False, default=str)


class NIS2JsonFormatter(AppJsonFormatter):
    """JSON formatter for NIS2-compliant audit entries. Inherits TZ and _now()."""

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "timestamp": self._now(),
            "level": record.levelname,
            "event_type": getattr(record, "event_type", None),
            "session_id": getattr(record, "session_id", None),
            "user": getattr(record, "user", None),
            "ip": getattr(record, "ip", None),
            "path": getattr(record, "path", None),
            "method": getattr(record, "method", None),
            "detail": getattr(record, "detail", {}),
        }
        return json.dumps(entry, ensure_ascii=False, default=str)
