# NIS2-Compliant Audit Logging — Design Spec

**Date:** 2026-03-20
**Branch:** `feature/nis2-compliance-logging`
**Status:** Approved

---

## Context

The GIS Dashboard DT Django application is operated by an **essential entity** under NIS2 (Directive 2022/2555). The application already has basic operational logging (rotating file handlers for `django.log` and `arcgis.log`, plain-text format), but lacks a structured audit trail meeting NIS2 Article 21 requirements.

**Gaps identified in the current implementation:**
- Authorization denials in `ServiceAccessMiddleware` are not logged
- No structured (JSON) log format for SIEM ingestion
- Log retention is ~50MB cap (days/weeks), far below the 12-month NIS2 minimum
- No separation between operational and audit logs
- No data access audit trail

---

## Requirements

- **Compliance scope:** NIS2 Article 21, essential entity obligations
- **SIEM target:** Google SecOps (Chronicle), ingested via Bindplane/Chronicle forwarder
- **Log storage:** Local files (primary) + Google SecOps (forwarded)
- **Retention:** 12 months total, 3 months immediately accessible on-disk
- **Tamper protection:** OS-level (append-only file, restricted directory permissions)
- **Audit scope:** Security events (full detail) + data access (summarized)

---

## Architecture

```
apps/audit/
├── __init__.py
├── apps.py
├── formatters.py       # NIS2JsonFormatter
├── signals.py          # User/group change handlers
└── utils.py            # emit_audit_event() — central emit function

config/settings.py      # audit_file handler + audit logger + NIS2JsonFormatter

logs/
├── django.log          # Operational logs (unchanged)
├── arcgis.log          # ArcGIS service logs (unchanged)
└── audit.log           # NIS2 audit trail (new, JSON, 365-day daily rotation)
```

**Note:** No `middleware.py` is included. Session expiry logging requires a dedicated session timeout middleware that is not yet implemented in this project; it is deferred to a future feature.

**Event flow:**

1. **Security events** (auth, authz, user/group changes) — captured by signals and updated auth views. No changes needed to business logic.
2. **Data access events** (report viewed, PDF exported, ArcGIS query, segnalazione viewed) — `emit_audit_event()` called explicitly at 6 instrumentation points in existing views/services.
3. Both write to the `audit` Python logger → `logs/audit.log` via `TimedRotatingFileHandler`.
4. Google SecOps Bindplane agent tails `audit.log` and forwards entries to Chronicle in near-real-time.

The existing operational loggers (`django.log`, `arcgis.log`) are **not modified**.

---

## Audit Event Taxonomy

| Category | `event_type` | Log level | Trigger | Key detail fields |
|---|---|---|---|---|
| Auth | `auth.login.success` | INFO | Successful login | `auth_method` (oidc/local) |
| Auth | `auth.login.failure` | WARNING | Failed login attempt | `username_attempted`, `attempt_count` |
| Auth | `auth.login.locked` | WARNING | Login while locked out | `username_attempted`, `attempt_count`, `locked_until` |
| Auth | `auth.logout` | INFO | Logout | — |
| Auth | `auth.user.created` | INFO | First Azure AD login | `email` |
| Authz | `authz.access.denied` | WARNING | ServiceAccessMiddleware denies | `app_label`, `reason` |
| Authz | `authz.group.changed` | INFO | User group membership actually changed | `groups_added`, `groups_removed`, `changed_by` |
| Data | `data.report.viewed` | INFO | Report list/detail page loaded | `report_id` |
| Data | `data.report.exported` | INFO | PDF export | `report_id` |
| Data | `data.arcgis.queried` | INFO | ArcGIS layer query | `layer_id`, `record_count` |
| Data | `data.segnalazione.viewed` | INFO | Segnalazioni list/detail | `segnalazione_id` |
| Admin | `admin.user.changed` | INFO | Django admin user edit | `user_changed`, `changed_by`, `fields` |

**`reason` values for `authz.access.denied`:**
- `"service_not_found"` — no active `Service` record exists for the app label (DEFAULT_POLICY is "deny")
- `"group_not_permitted"` — a `Service` record exists but the user's groups do not have access

---

## JSON Log Schema

Every audit entry is a single JSON line (`\n`-delimited):

```json
{
  "timestamp": "2026-03-20T11:46:00.123456+01:00",
  "level": "INFO",
  "event_type": "auth.login.success",
  "session_id": "a3f9b2c1d4e5f6a7b8c9d0e1f2a3b4c5",
  "user": "mario.rossi",
  "ip": "192.168.1.42",
  "path": "/auth/login/",
  "method": "POST",
  "detail": {
    "auth_method": "local"
  }
}
```

**Field rules:**

| Field | Type | Notes |
|---|---|---|
| `timestamp` | ISO 8601 string | With UTC offset (Europe/Rome); always present |
| `level` | string | See log level column in taxonomy table |
| `event_type` | string | Dotted namespace from taxonomy above |
| `session_id` | string or null | `request.session.session_key`; `null` only when no session has been created yet (e.g. anonymous request with no prior session) |
| `user` | string | Django `username`; `"anonymous"` if unauthenticated |
| `ip` | string | From `X-Forwarded-For` (first value) or `REMOTE_ADDR` |
| `path` | string | `request.path` — path only, no query string |
| `method` | string | HTTP method |
| `detail` | object | Event-specific payload; always an object, never null |

**Level-selection rule in `emit_audit_event()`:**

```python
WARNING_EVENT_TYPES = {
    "auth.login.failure",
    "auth.login.locked",
    "authz.access.denied",
}
level = logging.WARNING if event_type in WARNING_EVENT_TYPES else logging.INFO
```

---

## Component Details

### `formatters.py` — `NIS2JsonFormatter`

Subclasses `logging.Formatter`. Reads structured fields from the `LogRecord`'s `extra` dict and serializes the complete entry as a JSON line. Falls back gracefully for any missing field (uses `None`/empty string). Uses `datetime.now(tz)` with `ZoneInfo("Europe/Rome")` for the timestamp to include the correct UTC offset.

### `utils.py` — `emit_audit_event()`

```python
def emit_audit_event(request, event_type: str, detail: dict | None = None) -> None:
    ...
```

Single function callable from any view or service. Automatically extracts `user`, `ip`, `session_id`, `path`, and `method` from `request`. Callers only supply `event_type` and the event-specific `detail` dict.

- `user`: `request.user.username` if authenticated, `"anonymous"` otherwise
- `ip`: `request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()` or `request.META.get("REMOTE_ADDR")`
- `session_id`: `request.session.session_key` (may be `None` if no session yet)
- `path`: `request.path`
- `method`: `request.method`

Level is determined by `WARNING_EVENT_TYPES` set (see schema section).

### `signals.py`

**`authz.group.changed`** — connected to `m2m_changed` on `User.groups`. The handler **diffs old vs. new group membership** before emitting; it only emits when `groups_added` or `groups_removed` is non-empty. This prevents spurious events during `AzureOIDCBackend.sync_user()`, which calls `user.groups.remove()` and `user.groups.add()` on every OIDC login even when nothing changed.

The diff logic:
```python
# On m2m_changed pre_remove: capture current groups
# On m2m_changed post_add: compare and emit only if changed
```

`changed_by`: set to `"oidc_sync"` when triggered by the OIDC sync path, or the admin username when triggered via Django admin.

**`admin.user.changed`** — connected to `post_save` on `User` with `sender=User`. Emits only when the save originates from the Django admin (detected via `request` on the signal if available, or via `update_fields`).

Both handlers connected in `apps/audit/apps.py` `ready()` method.

### `apps/accounts/auth.py` — `auth.user.created`

`AzureOIDCBackend.create_user()` does not receive `request` as a parameter. However, `mozilla-django-oidc` sets `self.request` on the backend instance before calling `create_user`. The instrumentation uses `self.request`:

```python
emit_audit_event(self.request, "auth.user.created", detail={"email": email})
```

---

## Instrumentation Points in Existing Code

Minimal changes to existing files:

| File | Change |
|---|---|
| `apps/authorization/middleware.py` | Call `emit_audit_event()` on both `HttpResponseForbidden` paths with `reason="service_not_found"` and `reason="group_not_permitted"` respectively |
| `apps/accounts/views.py` | Replace `logger.*` auth calls with `emit_audit_event()`; `auth.login.locked` includes `attempt_count=login_attempts` and `locked_until=last_attempt + lockout_duration` |
| `apps/accounts/auth.py` | Replace `logger.info('Created new user...')` with `emit_audit_event(self.request, ...)` |
| `apps/reports/views/pages.py` | Add `emit_audit_event()` for report viewed |
| `apps/reports/views/pdf.py` | Add `emit_audit_event()` for PDF export |
| `apps/core/services/arcgis.py` | Add `emit_audit_event()` after successful layer query; requires passing `request` into the service method |
| `apps/segnalazioni/views/pages.py` | Add `emit_audit_event()` for segnalazione viewed |

**Note on `apps/core/services/arcgis.py`:** The `ArcGISService` class currently does not receive `request`. The `query_layer()` method signature must be extended to accept an optional `request` parameter. If `request` is `None`, the audit event is skipped (to avoid breaking non-request-context callers).

---

## Log Rotation & Retention

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
}
```

- Daily rotation at midnight → files named `audit.log.YYYY-MM-DD`
- 365 backups = 12 months on disk (plus the active `audit.log`, totalling ~366 days)
- 3-month "hot" requirement satisfied: all files are immediately accessible on disk
- Google SecOps provides the authoritative long-term retention per Chronicle license

**Deployment note (out of scope for this implementation):** The `logs/` directory must be owned by the app service account with no write access for other OS users. This is an infrastructure/deployment concern.

---

## Settings Changes

New additions to `config/settings.py`:

```python
LOGGING = {
    ...
    'formatters': {
        ...
        'audit_json': {
            '()': 'apps.audit.formatters.NIS2JsonFormatter',
        },
    },
    'handlers': {
        ...
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
    },
    'loggers': {
        ...
        'audit': {
            'handlers': ['audit_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
```

`apps.audit` added to `INSTALLED_APPS`. No new middleware is added.

---

## Testing

**Unit tests** (`apps/audit/tests.py`):

- `NIS2JsonFormatter` emits valid JSON with all required fields
- `NIS2JsonFormatter` uses ISO 8601 timestamp with UTC offset
- `emit_audit_event()` correctly extracts `user`, `ip`, `session_id`, `path`, `method` from a mock request
- `emit_audit_event()` uses `"anonymous"` for unauthenticated requests
- `emit_audit_event()` uses `null` session_id when `request.session.session_key` is `None`
- `emit_audit_event()` logs at `WARNING` for `auth.login.failure`, `auth.login.locked`, `authz.access.denied`
- `emit_audit_event()` logs at `INFO` for all other event types
- Each `event_type` value is present and correctly namespaced

**Integration tests** (Django `TestCase` + `assertLogs`):

- `auth.login.success` emitted on successful local login
- `auth.login.failure` emitted on bad credentials, includes `attempt_count`
- `auth.login.locked` emitted when login attempted during lockout; includes `attempt_count` and `locked_until`
- `auth.logout` emitted on logout
- `auth.user.created` emitted on first OIDC login (via `AzureOIDCBackend.create_user`)
- `authz.access.denied` with `reason="service_not_found"` emitted when no Service record exists
- `authz.access.denied` with `reason="group_not_permitted"` emitted when user lacks group access
- `authz.group.changed` emitted when user groups are actually modified (not on no-op sync)
- `authz.group.changed` NOT emitted when `sync_user` runs but groups are unchanged
- `admin.user.changed` emitted on Django admin user save
- `data.report.viewed` emitted on report list page load
- `data.report.exported` emitted on PDF export
- `data.arcgis.queried` emitted after ArcGIS layer query

**Out of scope:** log rotation timing, Google SecOps forwarding, OS file permissions.

---

## Non-Goals

- No in-app audit log viewer (Google SecOps handles search)
- No cryptographic log chaining
- No changes to `django.log` or `arcgis.log` format
- No Google SecOps Bindplane configuration (infrastructure concern)
- No session expiry logging (requires a dedicated session timeout middleware, deferred to a future feature)
