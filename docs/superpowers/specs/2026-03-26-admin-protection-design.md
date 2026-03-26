# Admin Endpoint Protection — Design Spec

**Date:** 2026-03-26
**Status:** Approved

## Problem

The Django admin endpoint has three unaddressed security gaps:

1. Hitting `/admin/` shows Django's username/password login form to unauthenticated users, bypassing the OIDC flow entirely.
2. Authenticated users who are not staff/superusers can reach the admin URL (currently in `EXEMPT_URL_PREFIXES`, so `ServiceAccessMiddleware` skips it).
3. The admin URL is at the predictable `/admin/` path and is not IP-restricted.

## Goals

- Redirect unauthenticated users to OIDC login instead of showing the Django login form.
- Block authenticated non-staff/non-superuser users with a 403.
- Restrict admin access to configurable IP addresses and CIDR ranges.
- Move admin to a non-predictable URL configured via environment variable.

## Architecture

A `SecureAdminSite` subclass of `django.contrib.admin.AdminSite` lives in `apps/authorization/admin_site.py`. The `authorization` app already owns access control for the project, making it the natural home.

The instance replaces `django.contrib.admin.site` in `AuthorizationConfig.ready()`, so all existing `@admin.register(Model)` decorators continue to work without modification.

Protection layers stack in order on every admin request:

```
Request → IP check → authenticated? → OIDC redirect → is_staff/superuser? → allow
```

## Components

### `apps/authorization/admin_site.py`

**`SecureAdminSite`** overrides two methods:

#### `has_permission(request)`

1. Extract client IP: use first entry of `X-Forwarded-For` if present, otherwise `REMOTE_ADDR`.
2. Parse `ADMIN_ALLOWED_IPS` (comma-separated IPs and CIDR ranges) into `ipaddress` network objects — parsed once at class instantiation, not per-request.
3. If the allowlist is non-empty and the client IP is not in any allowed range → return `False` (Django admin renders a 403).
4. Delegate to `super().has_permission()` for the `is_active and is_staff` check.

When `ADMIN_ALLOWED_IPS` is empty, the IP check is skipped entirely (dev-friendly default).

#### `login(request, extra_context=None)`

- If the user is **not authenticated** → redirect to `/oidc/authenticate/` (OIDC entry point).
- If the user is authenticated but `has_permission()` returned `False` → call `super().login()` which renders a 403/permission-denied page without a login form.

### `apps/authorization/apps.py`

In `AuthorizationConfig.ready()`, replace the default admin site:

```python
from django.contrib import admin
from .admin_site import secure_admin_site

admin.site = secure_admin_site
admin.sites.site = secure_admin_site
```

This ensures all `@admin.register()` decorators and `ModelAdmin` registrations point to the secured site.

### `config/urls.py`

Replace:
```python
path('admin/', admin.site.urls),
```
With:
```python
from apps.authorization.admin_site import secure_admin_site

path(f'{settings.ADMIN_URL}/', secure_admin_site.urls),
```

### `apps/authorization/middleware.py`

Remove the hardcoded `"/admin/"` from `EXEMPT_URL_PREFIXES`. Replace with a dynamic entry:

```python
EXEMPT_URL_PREFIXES = getattr(settings, "SERVICE_AUTH_EXEMPT_URLS", [
    "/oidc/",
    f"/{settings.ADMIN_URL}/",
    "/static/",
    "/health/",
    "/auth/",
    "/accounts/",
])
```

Admin is still exempt from `ServiceAccessMiddleware` because it has its own protection stack.

### `config/settings.py`

Two new settings:

```python
# Admin endpoint configuration
ADMIN_URL = os.getenv('ADMIN_URL', 'admin')
ADMIN_ALLOWED_IPS = os.getenv('ADMIN_ALLOWED_IPS', '')
```

- `ADMIN_URL`: The URL path segment for the admin (e.g. `mgmt-a3f9c2`). Defaults to `admin` so local dev requires no configuration.
- `ADMIN_ALLOWED_IPS`: Comma-separated IPs and CIDR ranges (e.g. `10.0.0.0/8,192.168.1.50`). Empty string disables IP restriction.

## Data Flow

```
Unauthenticated request to /<ADMIN_URL>/
  → SecureAdminSite.login()
  → redirect to /oidc/authenticate/

Authenticated request, IP not in allowlist
  → SecureAdminSite.has_permission() → False
  → 403

Authenticated request, IP allowed, not staff
  → SecureAdminSite.has_permission() → False (super() returns False)
  → 403

Authenticated request, IP allowed, is_staff=True
  → SecureAdminSite.has_permission() → True
  → admin rendered normally
```

## Error Handling

- Malformed CIDR in `ADMIN_ALLOWED_IPS` → raise `ValueError` at startup (fail fast, not silently).
- Malformed IP in `X-Forwarded-For` → fall back to `REMOTE_ADDR`.

## Testing

File: `apps/authorization/tests/test_admin_site.py`

| Scenario | Expected |
|---|---|
| Unauthenticated user hits admin URL | Redirect to `/oidc/authenticate/` |
| Authenticated non-staff user, IP allowed | 403 |
| Authenticated staff user, IP not in allowlist | 403 |
| Authenticated staff user, IP in allowlist | 200 |
| Authenticated superuser, IP not in allowlist | 403 |
| Authenticated superuser, IP in allowlist | 200 |
| `ADMIN_ALLOWED_IPS` empty | IP check skipped; staff/superuser allowed |
| CIDR range match (`192.168.1.0/24`, client `192.168.1.50`) | 200 |
| `X-Forwarded-For` header present | First IP in header used |
| Admin URL changed via `ADMIN_URL` env var | Old `/admin/` returns 404, new URL works |
| Malformed CIDR in `ADMIN_ALLOWED_IPS` | `ValueError` raised at startup |

All tests use Django's `TestClient` or `RequestFactory`. No live server required.

## Out of Scope

- Rate limiting or brute-force protection on the admin login (separate concern).
- Audit logging of admin access attempts (can be added as a follow-up via the existing audit app).
