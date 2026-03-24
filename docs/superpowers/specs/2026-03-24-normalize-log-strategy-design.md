# Normalize Log Strategy — Design Spec

**Date:** 2026-03-24
**Branch:** `feat/normalize-log-strategy`
**Status:** Approved

---

## Context

The project currently has two log files:

- `audit.log` — NIS2-compliant structured JSON audit trail (implemented in `feature/nis2-compliance-logging`)
- `arcgis.log` — ArcGIS service operational log, plain-text format via `verbose` formatter

`arcgis.log` is inconsistent with the rest of the logging infrastructure: it is plain text while `audit.log` is structured JSON. As new features are added, each will need operational logging; without a shared foundation, every module would either copy-paste formatting logic or produce logs in an incompatible format.

**Goals:**

1. Normalize `arcgis.log` to structured JSON.
2. Consolidate all feature operational logs into a single `app.log` with an `app` field identifying the source.
3. Provide a reusable `AppJsonFormatter` base class that future features can use without any settings changes.

---

## Architecture

```
logs/
├── audit.log     # NIS2 audit trail (unchanged)
└── app.log       # Shared operational log (new — replaces arcgis.log)

apps/audit/formatters.py
├── AppJsonFormatter      # Base: {timestamp, level, app, message}
└── NIS2JsonFormatter     # Extends AppJsonFormatter, adds NIS2 fields
```

`arcgis.log` is retired. The `arcgis_file` handler is replaced by `app_file`, pointing to `app.log` with `AppJsonFormatter`.

All loggers under the `apps.*` namespace automatically route to `app.log` via a single top-level `apps` logger in settings. New features using `logging.getLogger(__name__)` are captured without any additional configuration.

---

## `AppJsonFormatter` Schema

Every entry in `app.log` is a single JSON line:

```json
{
  "timestamp": "2026-03-24T10:23:00.123456+01:00",
  "level": "INFO",
  "app": "apps.core.services.arcgis",
  "message": "Successfully queried layer 0, returned 42 features"
}
```

| Field | Source | Notes |
|---|---|---|
| `timestamp` | `datetime.now(tz)` | ISO 8601 with UTC offset (Europe/Rome); same logic as `NIS2JsonFormatter` |
| `level` | `record.levelname` | Standard Python log level name |
| `app` | `record.name` | Logger name — equals `__name__` of the calling module |
| `message` | `record.getMessage()` | Formatted log message including any `%s` args |

---

## `NIS2JsonFormatter` Refactor

**Current state:** `NIS2JsonFormatter` is a standalone class with its own `TZ` and inline `datetime.now(tz=self.TZ).isoformat()` call. It does not subclass anything.

**After this change:** `NIS2JsonFormatter` subclasses `AppJsonFormatter`. This is a two-step refactor that must be done atomically:
1. Create `AppJsonFormatter` in `apps/audit/formatters.py`
2. Refactor `NIS2JsonFormatter` to extend `AppJsonFormatter` and call `self._now()`

The two formatters produce **completely different schemas** — they share only `TZ` (timezone constant) and `_now()` (the timestamp helper). `NIS2JsonFormatter` overrides `format()` entirely and calls `self._now()` for consistency.

The `message` field is **not** included in `audit.log` entries — `event_type` already serves as the semantic identifier there, and adding `message` would change a compliance-relevant schema. Similarly, `app` is not included in audit entries.

```python
class AppJsonFormatter(logging.Formatter):
    TZ = ZoneInfo("Europe/Rome")

    def _now(self) -> str:
        """Shared timestamp helper — ISO 8601 with Europe/Rome UTC offset."""
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
    """Inherits TZ and _now() from AppJsonFormatter. Produces a separate NIS2 schema."""

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
```

---

## Settings Changes

In `config/settings.py`:

**Implementation order** (required — settings reference classes that must exist first):
1. Refactor `apps/audit/formatters.py` (create `AppJsonFormatter`, update `NIS2JsonFormatter`)
2. Update `config/settings.py`

**Add** `app_json` formatter, `app_file` handler, `apps` logger.
**Remove** the `arcgis_file` handler definition entirely (note: `CompressedRotatingFileHandler` class stays — it is reused by `app_file`). Remove the `apps.core.services.arcgis` logger entry entirely — it will be caught automatically by the new `apps` prefix logger.

```python
'formatters': {
    # existing: verbose, audit_json (unchanged)
    'app_json': {
        '()': 'apps.audit.formatters.AppJsonFormatter',
    },
},
'handlers': {
    # existing: console, django_file, audit_file
    # remove: arcgis_file
    'app_file': {
        'level': 'DEBUG',
        'class': 'config.settings.CompressedRotatingFileHandler',  # reuse existing class
        'filename': BASE_DIR / 'logs' / 'app.log',
        'maxBytes': 1024 * 1024 * 10,  # 10 MB
        'backupCount': 5,
        'encoding': 'utf-8',
        'formatter': 'app_json',
    },
},
'loggers': {
    # existing: django, audit
    # remove: apps.core.services.arcgis
    'apps': {
        'handlers': ['app_file'],
        'level': 'DEBUG',
        'propagate': False,
    },
},
```

The `apps` logger prefix catches all `apps.*` loggers. New features require zero settings changes.

---

## Instrumentation Points

No changes to `apps/core/services/arcgis.py` — it already uses `logging.getLogger(__name__)`, which resolves to `apps.core.services.arcgis` and is captured by the `apps` logger prefix.

No changes to any other existing module.

---

## Future Feature Logging

A new feature module (e.g., hypothetically `apps/segnalazioni/services/data.py`) only needs:

```python
import logging
logger = logging.getLogger(__name__)
```

Its entries will automatically appear in `app.log` with `"app": "apps.segnalazioni.services.data"`. No settings change required.

---

## Testing

- `AppJsonFormatter` emits valid JSON with `timestamp`, `level`, `app`, `message` fields
- `AppJsonFormatter._now()` returns ISO 8601 format with Europe/Rome UTC offset (e.g. `+01:00` or `+02:00`)
- `AppJsonFormatter` `app` field equals `record.name`
- `AppJsonFormatter._now()` returns ISO 8601 format with Europe/Rome UTC offset
- `NIS2JsonFormatter` is a subclass of `AppJsonFormatter` (isinstance check)
- `NIS2JsonFormatter` does not override `_now()` — it inherits from `AppJsonFormatter`
- `NIS2JsonFormatter` output does NOT include `message` or `app` fields (audit schema unchanged)
- Existing NIS2 audit tests continue to pass unchanged

---

## Non-Goals

- No changes to `audit.log` format or schema
- No changes to `django.log`
- No log viewer or search UI
- No forwarding configuration changes (Google SecOps Bindplane)
- No `segnalazioni` ArcGIS instrumentation (stub not yet replaced with real calls)
