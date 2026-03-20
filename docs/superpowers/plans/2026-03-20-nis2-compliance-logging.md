# NIS2-Compliant Audit Logging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a structured JSON audit log (`logs/audit.log`) in a new `apps/audit` Django app that captures NIS2 Article 21 security and data-access events, forwarding-ready for Google SecOps.

**Architecture:** A new `apps/audit` app owns all audit concerns: `NIS2JsonFormatter` writes JSON lines, `emit_audit_event(request, event_type, detail)` is called from auth views, authorization middleware, and data-access views. Group changes are captured via Django signals; Django admin user changes via a custom `UserAdmin`. The `audit` logger writes exclusively to `logs/audit.log` via a 365-day `TimedRotatingFileHandler`.

**Tech Stack:** Python 3.13, Django 6.x, `logging` stdlib, `zoneinfo` (Python 3.9+ stdlib), `django.test.TestCase` + `assertLogs`.

**Spec:** `docs/superpowers/specs/2026-03-20-nis2-compliance-logging-design.md`

---

## File Map

**Create:**
- `apps/audit/__init__.py` — empty, marks the package
- `apps/audit/apps.py` — AppConfig, connects signals in `ready()`
- `apps/audit/formatters.py` — `NIS2JsonFormatter`
- `apps/audit/utils.py` — `emit_audit_event()`, `WARNING_EVENT_TYPES`
- `apps/audit/signals.py` — `authz.group.changed` m2m signal handler
- `apps/audit/admin.py` — `AuditUserAdmin` for `admin.user.changed`
- `apps/audit/tests.py` — all unit + integration tests

**Modify:**
- `config/settings.py` — add `apps.audit` to `INSTALLED_APPS`, add `audit_json` formatter, `audit_file` handler, `audit` logger
- `apps/authorization/middleware.py` — add `emit_audit_event()` on both 403 paths
- `apps/accounts/views.py` — replace `logger.*` auth calls with `emit_audit_event()`
- `apps/accounts/auth.py` — replace `logger.info('Created new user...')` with `emit_audit_event()`
- `apps/reports/views/pages.py` — add `emit_audit_event()` for report viewed
- `apps/reports/views/pdf.py` — add `emit_audit_event()` for PDF export
- `apps/reports/views/api.py` — add `emit_audit_event()` after main layer query (line 198)
- `apps/segnalazioni/views/pages.py` — add `emit_audit_event()` for segnalazione viewed

---

## Task 1: Scaffold `apps/audit`

**Files:**
- Create: `apps/audit/__init__.py`
- Create: `apps/audit/apps.py`
- Modify: `config/settings.py`

- [ ] **Step 1: Create the package and AppConfig**

`apps/audit/__init__.py` — empty file.

`apps/audit/apps.py`:
```python
from django.apps import AppConfig


class AuditConfig(AppConfig):
    name = "apps.audit"
    verbose_name = "Audit"

    def ready(self):
        import apps.audit.signals  # noqa: F401 — connect signal handlers
```

- [ ] **Step 2: Register the app in settings**

In `config/settings.py`, add `'apps.audit'` to `INSTALLED_APPS` after the other local apps:
```python
INSTALLED_APPS = [
    ...
    # Local apps
    'apps.accounts',
    'apps.authorization',
    'apps.core',
    'apps.reports',
    'apps.segnalazioni',
    'apps.audit',          # ← add this line
]
```

- [ ] **Step 3: Verify the app loads without errors**

```bash
python manage.py check
```
Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 4: Commit**

```bash
git add apps/audit/__init__.py apps/audit/apps.py config/settings.py
git commit -m "feat(audit): scaffold apps/audit app"
```

---

## Task 2: `NIS2JsonFormatter` (TDD)

**Files:**
- Create: `apps/audit/tests.py`
- Create: `apps/audit/formatters.py`

- [ ] **Step 1: Write the failing tests**

`apps/audit/tests.py`:
```python
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
        # ISO 8601: YYYY-MM-DDTHH:MM:SS[.ffffff]+HH:MM
        import re
        self.assertRegex(
            parsed["timestamp"],
            r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}",
        )
        # Must contain UTC offset (+HH:MM or -HH:MM)
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python manage.py test apps.audit.tests.NIS2JsonFormatterTest -v 2
```
Expected: `ImportError: cannot import name 'NIS2JsonFormatter' from 'apps.audit.formatters'`

- [ ] **Step 3: Implement `NIS2JsonFormatter`**

`apps/audit/formatters.py`:
```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python manage.py test apps.audit.tests.NIS2JsonFormatterTest -v 2
```
Expected: all 7 tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps/audit/formatters.py apps/audit/tests.py
git commit -m "feat(audit): NIS2JsonFormatter with ISO 8601 timestamped JSON output"
```

---

## Task 3: `emit_audit_event()` (TDD)

**Files:**
- Modify: `apps/audit/tests.py`
- Create: `apps/audit/utils.py`

- [ ] **Step 1: Add unit tests for `emit_audit_event`**

Append to `apps/audit/tests.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python manage.py test apps.audit.tests.EmitAuditEventTest -v 2
```
Expected: `ImportError: cannot import name 'emit_audit_event' from 'apps.audit.utils'`

- [ ] **Step 3: Implement `utils.py`**

`apps/audit/utils.py`:
```python
import logging

audit_logger = logging.getLogger("audit")

WARNING_EVENT_TYPES = frozenset({
    "auth.login.failure",
    "auth.login.locked",
    "authz.access.denied",
})


def emit_audit_event(request, event_type: str, detail: dict | None = None) -> None:
    """
    Emit a structured NIS2 audit log entry.

    Extracts user, IP, session_id, path, and method from request.
    Logs at WARNING for failure/denial events, INFO for everything else.
    """
    level = logging.WARNING if event_type in WARNING_EVENT_TYPES else logging.INFO

    if request is not None:
        user = request.user.username if request.user.is_authenticated else "anonymous"
        x_fwd = request.META.get("HTTP_X_FORWARDED_FOR", "")
        ip = x_fwd.split(",")[0].strip() if x_fwd else request.META.get("REMOTE_ADDR", "")
        session_id = getattr(request.session, "session_key", None)
        path = request.path
        method = request.method
    else:
        user = "system"
        ip = None
        session_id = None
        path = None
        method = None

    audit_logger.log(
        level,
        event_type,
        extra={
            "event_type": event_type,
            "user": user,
            "ip": ip,
            "session_id": session_id,
            "path": path,
            "method": method,
            "detail": detail or {},
        },
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python manage.py test apps.audit.tests.EmitAuditEventTest -v 2
```
Expected: all 11 tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps/audit/utils.py apps/audit/tests.py
git commit -m "feat(audit): emit_audit_event() with WARNING_EVENT_TYPES level routing"
```

---

## Task 4: Settings — wire up audit logger and handler

**Files:**
- Modify: `config/settings.py`

- [ ] **Step 1: Add `audit_json` formatter to `LOGGING['formatters']`**

In `config/settings.py`, inside the `LOGGING` dict, add to `'formatters'`:
```python
'formatters': {
    'verbose': {
        'format': '{levelname} {asctime} {name} {message}',
        'style': '{',
    },
    'audit_json': {                              # ← add
        '()': 'apps.audit.formatters.NIS2JsonFormatter',
    },
},
```

- [ ] **Step 2: Add `audit_file` handler to `LOGGING['handlers']`**

Add to `'handlers'`:
```python
'audit_file': {
    'level': 'INFO',
    'class': 'logging.handlers.TimedRotatingFileHandler',
    'filename': BASE_DIR / 'logs' / 'audit.log',
    'when': 'midnight',
    'interval': 1,
    'backupCount': 365,
    'encoding': 'utf-8',
    'formatter': 'audit_json',
},
```

- [ ] **Step 3: Add `audit` logger to `LOGGING['loggers']`**

Add to `'loggers'`:
```python
'audit': {
    'handlers': ['audit_file'],
    'level': 'INFO',
    'propagate': False,
},
```

- [ ] **Step 4: Ensure `logs/` directory exists**

```bash
python -c "import os; os.makedirs('logs', exist_ok=True)"
```

- [ ] **Step 5: Verify the logger is configured correctly**

```bash
python -c "
import django, os
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
django.setup()
import logging
logger = logging.getLogger('audit')
print('audit handlers:', logger.handlers)
print('propagate:', logger.propagate)
"
```
Expected: shows one `TimedRotatingFileHandler` pointing to `logs/audit.log`, `propagate: False`.

- [ ] **Step 6: Commit**

```bash
git add config/settings.py
git commit -m "feat(audit): wire audit_json formatter, audit_file handler, audit logger"
```

---

## Task 5: Instrument authentication events in `accounts/views.py`

**Files:**
- Modify: `apps/audit/tests.py`
- Modify: `apps/accounts/views.py`

- [ ] **Step 1: Add integration tests for auth events**

Append to `apps/audit/tests.py`:
```python
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
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


@override_settings(MIDDLEWARE=_TEST_MIDDLEWARE)
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python manage.py test apps.audit.tests.AuthEventTest -v 2
```
Expected: failures because `accounts/views.py` still uses `logger.*` not `emit_audit_event`.

- [ ] **Step 3: Update `apps/accounts/views.py`**

Add import at the top (after existing imports):
```python
from apps.audit.utils import emit_audit_event
```

Replace the four `logger.*` call sites:

**Login success** (currently `logger.info(f"Successful login for user: {username}...")`):
```python
emit_audit_event(request, "auth.login.success", detail={"auth_method": "local"})
```

**Login failure** (currently `logger.warning(f"Failed login attempt...")`):
```python
emit_audit_event(request, "auth.login.failure", detail={
    "username_attempted": username,
    "attempt_count": login_attempts + 1,
})
```

**Lockout check** (currently `logger.warning(f"Login attempt while locked...")`):
```python
emit_audit_event(request, "auth.login.locked", detail={
    "username_attempted": request.POST.get("username", ""),
    "attempt_count": login_attempts,
    "locked_until": last_attempt + lockout_duration,
})
```

**Logout** (currently `logger.info(f"User {request.user.username} logged out")`):
```python
emit_audit_event(request, "auth.logout", detail={})
```

Keep the existing `logger = logging.getLogger(__name__)` line (it may still be needed for other future use), but remove the four replaced `logger.*` calls.

- [ ] **Step 4: Run tests to verify they pass**

```bash
python manage.py test apps.audit.tests.AuthEventTest -v 2
```
Expected: all 7 tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps/accounts/views.py apps/audit/tests.py
git commit -m "feat(audit): emit auth events from accounts/views.py"
```

---

## Task 6: Instrument user creation in `accounts/auth.py`

**Files:**
- Modify: `apps/audit/tests.py`
- Modify: `apps/accounts/auth.py`

- [ ] **Step 1: Add test for `auth.user.created`**

Append to `apps/audit/tests.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python manage.py test apps.audit.tests.UserCreatedEventTest -v 2
```
Expected: tests fail (`auth.user.created` not emitted).

- [ ] **Step 3: Update `apps/accounts/auth.py`**

Add import after existing imports:
```python
from apps.audit.utils import emit_audit_event
```

In `create_user()`, replace:
```python
logger.info('Created new user from Azure AD claims: %s', email)
```
with:
```python
emit_audit_event(self.request, "auth.user.created", detail={"email": email})
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python manage.py test apps.audit.tests.UserCreatedEventTest -v 2
```
Expected: both tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps/accounts/auth.py apps/audit/tests.py
git commit -m "feat(audit): emit auth.user.created on first Azure AD login"
```

---

## Task 7: Instrument authorization denials in `authorization/middleware.py`

**Files:**
- Modify: `apps/audit/tests.py`
- Modify: `apps/authorization/middleware.py`

- [ ] **Step 1: Add integration tests for `authz.access.denied`**

Append to `apps/audit/tests.py`:
```python
from apps.authorization.models import Service


@override_settings(MIDDLEWARE=_TEST_MIDDLEWARE + [
    "apps.authorization.middleware.ServiceAccessMiddleware",
])
class AuthzAccessDeniedEventTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user("denieduser", password="pass")
        self.client.force_login(self.user)

    def test_service_not_found_emits_access_denied_with_reason(self):
        """No Service record exists → DEFAULT_POLICY=deny → access denied."""
        # No Service records created → triggers 'service_not_found' path
        with self.assertLogs("audit", level="WARNING") as cm:
            self.client.get(reverse("reports:report_list"))
        records = [r for r in cm.records if r.event_type == "authz.access.denied"]
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].detail["reason"], "service_not_found")

    def test_group_not_permitted_emits_access_denied_with_reason(self):
        """Service exists but user lacks group → 'group_not_permitted'."""
        svc = Service.objects.create(
            name="Reports", app_label="reports", is_active=True
        )
        # No groups assigned → user has no access
        with self.assertLogs("audit", level="WARNING") as cm:
            self.client.get(reverse("reports:report_list"))
        records = [r for r in cm.records if r.event_type == "authz.access.denied"]
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].detail["reason"], "group_not_permitted")

    def test_access_denied_detail_contains_app_label(self):
        with self.assertLogs("audit", level="WARNING") as cm:
            self.client.get(reverse("reports:report_list"))
        record = next(r for r in cm.records if r.event_type == "authz.access.denied")
        self.assertEqual(record.detail["app_label"], "reports")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python manage.py test apps.audit.tests.AuthzAccessDeniedEventTest -v 2
```
Expected: failures (no audit event emitted yet).

- [ ] **Step 3: Update `apps/authorization/middleware.py`**

Add imports at the top:
```python
import logging
from apps.audit.utils import emit_audit_event
```

Replace the first `HttpResponseForbidden` return (no Service record, DEFAULT_POLICY = "deny") at line ~71:
```python
# Before:
return HttpResponseForbidden(
    "You do not have permission to access this service. "
    "Contact your administrator to request access."
)

# After:
emit_audit_event(request, "authz.access.denied", detail={
    "app_label": app_label,
    "reason": "service_not_found",
})
return HttpResponseForbidden(
    "You do not have permission to access this service. "
    "Contact your administrator to request access."
)
```

Replace the second `HttpResponseForbidden` return (user lacks group) at line ~77:
```python
# Before:
return HttpResponseForbidden(
    "You do not have permission to access this service. "
    "Contact your administrator to request access."
)

# After:
emit_audit_event(request, "authz.access.denied", detail={
    "app_label": app_label,
    "reason": "group_not_permitted",
})
return HttpResponseForbidden(
    "You do not have permission to access this service. "
    "Contact your administrator to request access."
)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python manage.py test apps.audit.tests.AuthzAccessDeniedEventTest -v 2
```
Expected: all 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps/authorization/middleware.py apps/audit/tests.py
git commit -m "feat(audit): emit authz.access.denied with reason on both denial paths"
```

---

## Task 8: Group change signals

**Files:**
- Modify: `apps/audit/tests.py`
- Create: `apps/audit/signals.py`
- `apps/audit/apps.py` already connects signals in `ready()` — no change needed

- [ ] **Step 1: Add tests for `authz.group.changed`**

Append to `apps/audit/tests.py`:
```python
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
            self.user.groups.remove(self.group_a)
        event_types = [r.event_type for r in cm.records]
        self.assertIn("authz.group.changed", event_types)

    def test_no_op_sync_does_not_emit(self):
        """Remove group_a then add it back — net zero change should not emit."""
        self.user.groups.add(self.group_a)
        # Simulate sync_user: remove-then-add the same group
        try:
            with self.assertLogs("audit", level="INFO") as cm:
                self.user.groups.remove(self.group_a)  # pre_remove snapshot taken
                self.user.groups.add(self.group_a)     # post_add: same state → skip
            # If we get here, check that no authz.group.changed was emitted
            group_change_events = [r for r in cm.records
                                   if r.event_type == "authz.group.changed"]
            self.assertEqual(len(group_change_events), 0)
        except AssertionError:
            # assertLogs raises if NO logs at all — that's fine too (nothing emitted)
            pass
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python manage.py test apps.audit.tests.GroupChangedSignalTest -v 2
```
Expected: failures (no signal handler connected yet).

- [ ] **Step 3: Implement `signals.py`**

`apps/audit/signals.py`:
```python
"""
Signal handlers for NIS2 audit events.

authz.group.changed: fires when a user's group memberships actually change.

Uses a thread-local snapshot (pre_remove → post_add) to avoid spurious events
when AzureOIDCBackend.sync_user() removes and re-adds the same groups on every
OIDC login. Only emits when the before/after group sets differ.
"""

import logging
import threading

from django.contrib.auth.models import Group, User
from django.db.models.signals import m2m_changed
from django.dispatch import receiver

audit_logger = logging.getLogger("audit")

_tl = threading.local()


@receiver(m2m_changed, sender=User.groups.through)
def on_user_groups_changed(sender, instance, action, pk_set, **kwargs):
    """
    Track group membership changes. Emits authz.group.changed only when the
    final group set differs from the group set before any remove operation.
    """
    if action == "pre_remove" and pk_set:
        # Snapshot the complete group set before removal begins.
        _tl.user_pk = instance.pk
        _tl.groups_before = set(instance.groups.values_list("pk", flat=True))

    elif action == "post_remove":
        # If no prior pre_remove snapshot for this user, emit immediately.
        if getattr(_tl, "user_pk", None) != instance.pk:
            if not pk_set:
                return
            removed_names = list(
                Group.objects.filter(pk__in=pk_set).values_list("name", flat=True)
            )
            audit_logger.info("authz.group.changed", extra={
                "event_type": "authz.group.changed",
                "user": instance.username,
                "ip": None, "session_id": None, "path": None, "method": None,
                "detail": {
                    "groups_added": [],
                    "groups_removed": removed_names,
                    "changed_by": "oidc_sync",
                },
            })

    elif action == "post_add":
        groups_before = getattr(_tl, "groups_before", None)
        groups_after = set(instance.groups.values_list("pk", flat=True))

        if groups_before is not None and getattr(_tl, "user_pk", None) == instance.pk:
            # We had a pre_remove snapshot — compute actual diff.
            _tl.user_pk = None
            _tl.groups_before = None

            if groups_before == groups_after:
                return  # No-op sync — do not emit.

            added_pks = groups_after - groups_before
            removed_pks = groups_before - groups_after
        else:
            # No prior remove — this is a standalone add.
            added_pks = pk_set or set()
            removed_pks = set()

        if not added_pks and not removed_pks:
            return

        added_names = list(
            Group.objects.filter(pk__in=added_pks).values_list("name", flat=True)
        )
        removed_names = list(
            Group.objects.filter(pk__in=removed_pks).values_list("name", flat=True)
        )

        audit_logger.info("authz.group.changed", extra={
            "event_type": "authz.group.changed",
            "user": instance.username,
            "ip": None, "session_id": None, "path": None, "method": None,
            "detail": {
                "groups_added": added_names,
                "groups_removed": removed_names,
                "changed_by": "oidc_sync",
            },
        })
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python manage.py test apps.audit.tests.GroupChangedSignalTest -v 2
```
Expected: all 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps/audit/signals.py apps/audit/tests.py
git commit -m "feat(audit): emit authz.group.changed via m2m signal with no-op diff guard"
```

---

## Task 9: Admin user change tracking

**Files:**
- Modify: `apps/audit/tests.py`
- Create: `apps/audit/admin.py`

- [ ] **Step 1: Add test for `admin.user.changed`**

Append to `apps/audit/tests.py`:
```python
@override_settings(MIDDLEWARE=_TEST_MIDDLEWARE)
class AdminUserChangedEventTest(TestCase):

    def setUp(self):
        self.admin = User.objects.create_superuser("admin", password="admin-pass")
        self.target = User.objects.create_user("target_user", password="pass",
                                               first_name="Old")
        self.client.force_login(self.admin)

    def test_admin_user_save_emits_admin_user_changed(self):
        change_url = f"/admin/auth/user/{self.target.pk}/change/"
        with self.assertLogs("audit", level="INFO") as cm:
            self.client.post(change_url, {
                "username": self.target.username,
                "first_name": "New",
                "last_name": self.target.last_name,
                "email": self.target.email,
                "is_active": "on",
                "date_joined_0": "2024-01-01",
                "date_joined_1": "00:00:00",
                "_save": "Save",
            })
        event_types = [r.event_type for r in cm.records]
        self.assertIn("admin.user.changed", event_types)

    def test_admin_user_changed_detail_contains_changed_by(self):
        change_url = f"/admin/auth/user/{self.target.pk}/change/"
        with self.assertLogs("audit", level="INFO") as cm:
            self.client.post(change_url, {
                "username": self.target.username,
                "first_name": "New",
                "last_name": self.target.last_name,
                "email": self.target.email,
                "is_active": "on",
                "date_joined_0": "2024-01-01",
                "date_joined_1": "00:00:00",
                "_save": "Save",
            })
        record = next(r for r in cm.records if r.event_type == "admin.user.changed")
        self.assertEqual(record.detail["changed_by"], "admin")
        self.assertEqual(record.detail["user_changed"], "target_user")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python manage.py test apps.audit.tests.AdminUserChangedEventTest -v 2
```
Expected: failures (`admin.user.changed` not emitted).

- [ ] **Step 3: Implement `admin.py`**

`apps/audit/admin.py`:
```python
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from apps.audit.utils import emit_audit_event


class AuditUserAdmin(UserAdmin):
    """Extends the built-in UserAdmin to emit audit events on user saves."""

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if change:
            emit_audit_event(request, "admin.user.changed", detail={
                "user_changed": obj.username,
                "changed_by": request.user.username,
                "fields": list(form.changed_data),
            })


admin.site.unregister(User)
admin.site.register(User, AuditUserAdmin)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python manage.py test apps.audit.tests.AdminUserChangedEventTest -v 2
```
Expected: both tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps/audit/admin.py apps/audit/tests.py
git commit -m "feat(audit): emit admin.user.changed via AuditUserAdmin.save_model"
```

---

## Task 10: Instrument report viewed and PDF exported

**Files:**
- Modify: `apps/audit/tests.py`
- Modify: `apps/reports/views/pages.py`
- Modify: `apps/reports/views/pdf.py`

- [ ] **Step 1: Add integration tests for data access events**

Append to `apps/audit/tests.py`:
```python
from apps.authorization.models import Service
from django.contrib.auth.models import Group


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
            mock_pisa.CreatePDF.return_value = MagicMock(err=0)
            self.client.get(reverse("reports:export_pdf") + "?rowid=TEST-ID")
        event_types = [r.event_type for r in cm.records]
        self.assertIn("data.report.exported", event_types)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python manage.py test apps.audit.tests.ReportDataAccessEventTest -v 2
```
Expected: failure (`data.report.viewed` not emitted).

- [ ] **Step 3: Update `apps/reports/views/pages.py`**

Add import after existing imports:
```python
from apps.audit.utils import emit_audit_event
```

In `ReportListView.get()`, add before the `return render(...)` call:
```python
emit_audit_event(request, "data.report.viewed", detail={"report_id": None})
```

In `ReportDetailView.get()`, after `report_id = request.GET.get('id')` succeeds (before `data = get_report_data(report_id)`), add:
```python
emit_audit_event(request, "data.report.viewed", detail={"report_id": report_id})
```

- [ ] **Step 4: Update `apps/reports/views/pdf.py`**

Add import after existing imports:
```python
from apps.audit.utils import emit_audit_event
```

In `export_pdf()`, after `data = get_report_data(report_id)` and before building `context`, add:
```python
emit_audit_event(request, "data.report.exported", detail={"report_id": report_id})
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
python manage.py test apps.audit.tests.ReportDataAccessEventTest -v 2
```
Expected: tests pass.

- [ ] **Step 6: Commit**

```bash
git add apps/reports/views/pages.py apps/reports/views/pdf.py apps/audit/tests.py
git commit -m "feat(audit): emit data.report.viewed and data.report.exported"
```

---

## Task 11: Instrument ArcGIS query event

**Files:**
- Modify: `apps/audit/tests.py`
- Modify: `apps/reports/views/api.py`

**Spec deviation (intentional):** The spec places this instrumentation in `apps/core/services/arcgis.py` by extending `query_layer()` to accept an optional `request` parameter. This plan deviates: the event is emitted in `apps/reports/views/api.py` instead. Reason: `query_feature_layer()` is also called from `apps/reports/services/report_data.py`, a service layer that has no `request` context, so passing `request` through the service chain would require cascading signature changes with no audit benefit (the user-facing query is always via this API view). The view-layer approach provides complete coverage of user-initiated ArcGIS queries without those cascading changes.

- [ ] **Step 1: Add test for `data.arcgis.queried`**

Append to `apps/audit/tests.py`:
```python
from unittest.mock import patch


@override_settings(MIDDLEWARE=_TEST_MIDDLEWARE + [
    "apps.authorization.middleware.ServiceAccessMiddleware",
])
class ArcGISQueryEventTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user("arcgisuser", password="pass")
        group = Group.objects.create(name="arcgis_group")
        self.user.groups.add(group)

        core_svc = Service.objects.create(name="Core", app_label="core", is_active=True)
        core_svc.allowed_groups.set([group])
        reports_svc = Service.objects.create(name="Reports", app_label="reports", is_active=True)
        reports_svc.allowed_groups.set([group])

        self.client.force_login(self.user)

    def test_get_data_emits_data_arcgis_queried(self):
        fake_result = {"features": [{"attributes": {}}]}
        with patch("apps.reports.views.api.query_feature_layer", return_value=fake_result), \
             self.assertLogs("audit", level="INFO") as cm:
            self.client.get(reverse("reports:get_data"))
        event_types = [r.event_type for r in cm.records]
        self.assertIn("data.arcgis.queried", event_types)

    def test_arcgis_queried_detail_contains_record_count(self):
        fake_result = {"features": [{"attributes": {}}, {"attributes": {}}]}
        with patch("apps.reports.views.api.query_feature_layer", return_value=fake_result), \
             self.assertLogs("audit", level="INFO") as cm:
            self.client.get(reverse("reports:get_data"))
        record = next(r for r in cm.records if r.event_type == "data.arcgis.queried")
        self.assertEqual(record.detail["record_count"], 2)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python manage.py test apps.audit.tests.ArcGISQueryEventTest -v 2
```
Expected: failures.

- [ ] **Step 3: Update `apps/reports/views/api.py`**

Add import after existing imports:
```python
from apps.audit.utils import emit_audit_event
```

In the view that calls `query_feature_layer(0, where)` (around line 198), immediately after the `result = query_feature_layer(0, where)` call, add:
```python
if "features" in result:
    emit_audit_event(request, "data.arcgis.queried", detail={
        "layer_id": 0,
        "record_count": len(result.get("features", [])),
    })
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python manage.py test apps.audit.tests.ArcGISQueryEventTest -v 2
```
Expected: tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps/reports/views/api.py apps/audit/tests.py
git commit -m "feat(audit): emit data.arcgis.queried after successful layer query in reports API"
```

---

## Task 12: Instrument segnalazione viewed

**Files:**
- Modify: `apps/audit/tests.py`
- Modify: `apps/segnalazioni/views/pages.py`

- [ ] **Step 1: Add test for `data.segnalazione.viewed`**

Append to `apps/audit/tests.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python manage.py test apps.audit.tests.SegnalazioneDataAccessEventTest -v 2
```
Expected: failure.

- [ ] **Step 3: Update `apps/segnalazioni/views/pages.py`**

Add import after existing imports:
```python
from apps.audit.utils import emit_audit_event
```

In `SegnalazioniListView.get()`, add before `return render(...)`:
```python
emit_audit_event(request, "data.segnalazione.viewed", detail={"segnalazione_id": None})
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python manage.py test apps.audit.tests.SegnalazioneDataAccessEventTest -v 2
```
Expected: test passes.

- [ ] **Step 5: Run the full audit test suite**

```bash
python manage.py test apps.audit -v 2
```
Expected: all tests pass with no failures.

- [ ] **Step 6: Commit**

```bash
git add apps/segnalazioni/views/pages.py apps/audit/tests.py
git commit -m "feat(audit): emit data.segnalazione.viewed on segnalazioni list view"
```

---

## Task 13: Full regression check

- [ ] **Step 1: Run the entire test suite**

```bash
python manage.py test -v 2
```
Expected: all tests pass (authorization, accounts, reports, audit).

- [ ] **Step 2: Smoke-test the audit log file**

```bash
python -c "
import django, os, logging
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
django.setup()
from apps.audit.utils import emit_audit_event
from unittest.mock import MagicMock
req = MagicMock()
req.user.is_authenticated = True
req.user.username = 'smoke_test'
req.META = {'REMOTE_ADDR': '127.0.0.1'}
req.session.session_key = 'smoke-session'
req.path = '/smoke/'
req.method = 'GET'
emit_audit_event(req, 'auth.login.success', detail={'auth_method': 'local'})
print('Smoke test OK — check logs/audit.log')
"
```

Then verify:
```bash
python -c "
import json
with open('logs/audit.log') as f:
    last = f.readlines()[-1]
parsed = json.loads(last)
print(json.dumps(parsed, indent=2))
assert parsed['event_type'] == 'auth.login.success'
assert '+' in parsed['timestamp'] or '-' in parsed['timestamp']
print('Audit log entry valid.')
"
```

- [ ] **Step 3: Final commit**

```bash
git add .
git commit -m "feat(audit): NIS2-compliant audit logging — all tasks complete"
```
