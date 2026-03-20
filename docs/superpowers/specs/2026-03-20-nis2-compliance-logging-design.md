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
- No session lifecycle events
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
├── middleware.py       # AuditMiddleware (session expiry events)
├── signals.py          # User/group change handlers
└── utils.py            # emit_audit_event() — central emit function

config/settings.py      # audit_file handler + audit logger + NIS2JsonFormatter

logs/
├── django.log          # Operational logs (unchanged)
├── arcgis.log          # ArcGIS service logs (unchanged)
└── audit.log           # NIS2 audit trail (new, JSON, 365-day daily rotation)
```

**Event flow:**

1. **Security events** (auth, authz, user/group changes) — captured automatically by `AuditMiddleware`, signals, and updated auth views. No changes needed to business logic.
2. **Data access events** (report viewed, PDF exported, ArcGIS query, segnalazione viewed) — `emit_audit_event()` called explicitly at 5–6 instrumentation points in existing views/services.
3. Both write to the `audit` Python logger → `logs/audit.log` via `TimedRotatingFileHandler`.
4. Google SecOps Bindplane agent tails `audit.log` and forwards entries to Chronicle in near-real-time.

The existing operational loggers (`django.log`, `arcgis.log`) are **not modified**.

---

## Audit Event Taxonomy

| Category | `event_type` | Trigger | Key detail fields |
|---|---|---|---|
| Auth | `auth.login.success` | Successful login | `auth_method` (oidc/local) |
| Auth | `auth.login.failure` | Failed login attempt | `username_attempted`, `attempt_count` |
| Auth | `auth.login.locked` | Login while locked out | `username_attempted` |
| Auth | `auth.logout` | Logout | — |
| Auth | `auth.user.created` | First Azure AD login | `email` |
| Auth | `auth.session.expired` | Session timeout redirect | — |
| Authz | `authz.access.denied` | ServiceAccessMiddleware denies | `app_label`, `reason` |
| Authz | `authz.group.changed` | User group membership change | `groups_added`, `groups_removed`, `changed_by` |
| Data | `data.report.viewed` | Report list/detail page loaded | `report_id` |
| Data | `data.report.exported` | PDF export | `report_id` |
| Data | `data.arcgis.queried` | ArcGIS layer query | `layer_id`, `record_count` |
| Data | `data.segnalazione.viewed` | Segnalazioni list/detail | `segnalazione_id` |
| Admin | `admin.user.changed` | Django admin user edit | `user_changed`, `changed_by`, `fields` |

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
| `level` | string | `INFO` for normal events, `WARNING` for failures/denials |
| `event_type` | string | Dotted namespace from taxonomy above |
| `session_id` | string or null | Django session key; `null` for pre-session events |
| `user` | string | Django `username`; `"anonymous"` if unauthenticated |
| `ip` | string | From `X-Forwarded-For` or `REMOTE_ADDR` |
| `path` | string | Request path |
| `method` | string | HTTP method |
| `detail` | object | Event-specific payload; always an object, never null |

---

## Component Details

### `formatters.py` — `NIS2JsonFormatter`

Subclasses `logging.Formatter`. Reads structured fields from the `LogRecord`'s `extra` dict and serializes the complete entry as a JSON line. Falls back gracefully for any missing field (uses `None`/empty string). Uses `datetime.now(tz)` for timestamp to include the correct UTC offset.

### `utils.py` — `emit_audit_event()`

```python
def emit_audit_event(request, event_type: str, detail: dict | None = None) -> None:
    ...
```

Single function callable from any view or service. Automatically extracts `user`, `ip`, `session_id`, `path`, and `method` from `request`. Callers only supply `event_type` and the event-specific `detail` dict. Logs to the `audit` logger at `INFO` or `WARNING` level based on the event type.

### `middleware.py` — `AuditMiddleware`

Sits after `AuthenticationMiddleware` in the middleware stack. On each response, detects session timeout redirects (redirect to login with `?timeout=1`) and emits `auth.session.expired`. All other security events (auth, authz) are emitted by the components that own those decisions.

### `signals.py`

- `m2m_changed` on `User.groups` → emits `authz.group.changed`
- `post_save` on `User` via Django admin → emits `admin.user.changed`

Connected in `apps/audit/apps.py` `ready()` method.

---

## Instrumentation Points in Existing Code

Minimal changes to existing files:

| File | Change |
|---|---|
| `apps/authorization/middleware.py` | Call `emit_audit_event()` on both `HttpResponseForbidden` paths |
| `apps/accounts/views.py` | Replace `logger.*` auth calls with `emit_audit_event()` |
| `apps/accounts/auth.py` | Replace `logger.info('Created new user...')` with `emit_audit_event()` |
| `apps/reports/views/pages.py` | Add `emit_audit_event()` for report viewed |
| `apps/reports/views/pdf.py` | Add `emit_audit_event()` for PDF export |
| `apps/core/services/arcgis.py` | Add `emit_audit_event()` after successful layer query |
| `apps/segnalazioni/views/pages.py` | Add `emit_audit_event()` for segnalazione viewed |

---

## Log Rotation & Retention

```python
'audit_file': {
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
- 365 backups = 12 months on disk
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

`AuditMiddleware` inserted after `AuthenticationMiddleware` in `MIDDLEWARE`.
`apps.audit` added to `INSTALLED_APPS`.

---

## Testing

**Unit tests** (`apps/audit/tests.py`):

- `NIS2JsonFormatter` emits valid JSON with all required fields
- `NIS2JsonFormatter` uses ISO 8601 timestamp with UTC offset
- `emit_audit_event()` correctly extracts `user`, `ip`, `session_id`, `path`, `method` from a mock request
- `emit_audit_event()` uses `"anonymous"` for unauthenticated requests
- `emit_audit_event()` uses `null` session_id when no session exists
- Each `event_type` constant is present and correctly namespaced

**Integration tests** (Django `TestCase` + `assertLogs`):

- `auth.login.success` emitted on successful local login
- `auth.login.failure` emitted on bad credentials, includes `attempt_count`
- `auth.login.locked` emitted when login attempted during lockout
- `auth.logout` emitted on logout
- `auth.user.created` emitted on first OIDC login (via `create_user`)
- `authz.access.denied` emitted on both denial paths in `ServiceAccessMiddleware`
- `authz.group.changed` emitted when user groups are modified
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
