import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo


class NIS2JsonFormatter(logging.Formatter):
    """JSON log formatter for NIS2-compliant audit entries."""

    TZ = ZoneInfo("Europe/Rome")

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "timestamp": datetime.now(tz=self.TZ).isoformat(),
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
