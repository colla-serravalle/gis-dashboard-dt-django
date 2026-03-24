# Normalize Log Strategy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the plain-text `arcgis.log` with a structured JSON `app.log` shared by all `apps.*` modules, by introducing `AppJsonFormatter` as a base class and refactoring `NIS2JsonFormatter` to inherit from it.

**Architecture:** `AppJsonFormatter` provides `TZ`, `_now()`, and a `format()` that emits `{timestamp, level, app, message}`. `NIS2JsonFormatter` subclasses it, inheriting `_now()` but overriding `format()` to produce the NIS2 audit schema. A single `apps` logger prefix in settings routes all `apps.*` loggers to `app.log` automatically.

**Tech Stack:** Python 3.13, Django 5.x, `zoneinfo`, `logging`, `json`

---

## Branch Setup

Before any code changes, create and switch to the feature branch:

```bash
git checkout -b feat/normalize-log-strategy
```

---

## File Map

| File | Action | What changes |
|---|---|---|
| `apps/audit/formatters.py` | Modify | Add `AppJsonFormatter`; refactor `NIS2JsonFormatter` to subclass it |
| `apps/audit/tests.py` | Modify | Add tests for `AppJsonFormatter` and inheritance |
| `config/settings.py` | Modify | Add `app_json` formatter + `app_file` handler + `apps` logger; remove `arcgis_file` handler and `apps.core.services.arcgis` logger |

No other files change. `apps/core/services/arcgis.py` already uses `logging.getLogger(__name__)` — no modifications needed.

---

## Task 1: Refactor `apps/audit/formatters.py` (TDD)

**Files:**
- Modify: `apps/audit/formatters.py`
- Modify: `apps/audit/tests.py`

- [ ] **Step 1: Write failing tests for `AppJsonFormatter`**

Open `apps/audit/tests.py`. Find the existing formatter test class (search for `NIS2JsonFormatter`). Add a new test class **before** it:

```python
import logging


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
        import re
        fmt = AppJsonFormatter()
        data = json.loads(fmt.format(self._make_record()))
        # Matches e.g. 2026-03-24T10:23:00.123456+01:00
        self.assertRegex(data["timestamp"], r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.*[+-]\d{2}:\d{2}")

    def test_now_returns_iso8601_with_utc_offset(self):
        from apps.audit.formatters import AppJsonFormatter
        import re
        fmt = AppJsonFormatter()
        ts = fmt._now()
        self.assertRegex(ts, r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.*[+-]\d{2}:\d{2}")
```

Also add an inheritance test class right after:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python manage.py test apps.audit.tests.AppJsonFormatterTest apps.audit.tests.NIS2FormatterInheritanceTest -v 2
```

Expected: All new tests fail with `ImportError: cannot import name 'AppJsonFormatter'` or similar.

- [ ] **Step 3: Implement `AppJsonFormatter` and refactor `NIS2JsonFormatter`**

Replace the entire contents of `apps/audit/formatters.py` with:

```python
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
```

- [ ] **Step 4: Run new tests to verify they pass**

```bash
python manage.py test apps.audit.tests.AppJsonFormatterTest apps.audit.tests.NIS2FormatterInheritanceTest -v 2
```

Expected: All 9 new tests pass.

- [ ] **Step 5: Run full audit test suite to verify no regressions**

```bash
python manage.py test apps.audit -v 2
```

Expected: All tests pass (previously passing NIS2 tests still green).

- [ ] **Step 6: Commit**

```bash
git add apps/audit/formatters.py apps/audit/tests.py
git commit -m "refactor(audit): introduce AppJsonFormatter base class

NIS2JsonFormatter now subclasses AppJsonFormatter, inheriting TZ
and _now(). Both formatters share timezone logic; schemas remain
independent."
```

---

## Task 2: Update `config/settings.py`

**Files:**
- Modify: `config/settings.py`

**Prerequisite:** Task 1 must be fully committed before this step. Django will import `AppJsonFormatter` at startup — the class must exist first.

- [ ] **Step 1: Add `app_json` formatter**

In `config/settings.py`, inside the `LOGGING['formatters']` dict, add after the `audit_json` entry:

```python
        'app_json': {
            '()': 'apps.audit.formatters.AppJsonFormatter',
        },
```

Result should look like:

```python
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {name} {message}',
            'style': '{',
        },
        'audit_json': {
            '()': 'apps.audit.formatters.NIS2JsonFormatter',
        },
        'app_json': {
            '()': 'apps.audit.formatters.AppJsonFormatter',
        },
    },
```

- [ ] **Step 2: Add `app_file` handler and remove `arcgis_file`**

In `config/settings.py`, inside `LOGGING['handlers']`:

**Remove** the entire `arcgis_file` block:
```python
        'arcgis_file': {
            'level': 'DEBUG',
            'class': 'config.settings.CompressedRotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'arcgis.log',
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
```

**Add** `app_file` in its place:
```python
        'app_file': {
            'level': 'DEBUG',
            'class': 'config.settings.CompressedRotatingFileHandler',  # reuse existing class
            'filename': BASE_DIR / 'logs' / 'app.log',
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 5,
            'encoding': 'utf-8',
            'formatter': 'app_json',
        },
```

- [ ] **Step 3: Add `apps` logger and remove `apps.core.services.arcgis`**

In `config/settings.py`, inside `LOGGING['loggers']`:

**Remove** the entire `apps.core.services.arcgis` entry:
```python
        'apps.core.services.arcgis': {
            'handlers': ['arcgis_file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
```

**Add** the `apps` prefix logger in its place:
```python
        'apps': {
            'handlers': ['app_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
```

The final `LOGGING['loggers']` section should contain: `django.request`, `apps`, `audit`.

- [ ] **Step 4: Run the full test suite**

```bash
python manage.py test apps.audit -v 2
```

Expected: All tests pass.

- [ ] **Step 5: Start the dev server and verify `app.log` is created**

```bash
python manage.py runserver
```

Then in a separate terminal, make a request that triggers ArcGIS logging (or simply check that `logs/app.log` is created on startup). Verify `app.log` contains valid JSON lines, e.g.:

```json
{"timestamp": "2026-03-24T10:23:00+01:00", "level": "DEBUG", "app": "apps.core.services.arcgis", "message": "ArcGIS token found in cache"}
```

Also confirm `logs/arcgis.log` is no longer written to (old file may still exist, but no new entries).

Stop the server (`Ctrl+C`) when done.

- [ ] **Step 6: Commit**

```bash
git add config/settings.py
git commit -m "feat(logging): replace arcgis.log with shared app.log

Retires arcgis_file handler and apps.core.services.arcgis logger.
Adds app_file handler (JSON, 10 MB rotating) and apps prefix logger
so all apps.* modules write structured JSON to app.log automatically."
```

---

## Done

Both tasks complete. Verify the branch is ready:

```bash
git log --oneline feat/normalize-log-strategy ^main
```

Expected: 2 commits — the formatters refactor and the settings update.
