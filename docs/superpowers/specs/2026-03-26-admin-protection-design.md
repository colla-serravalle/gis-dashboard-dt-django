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

### Site Registration Ordering (Critical)

`@admin.register(Model)` decorators execute at **import time**, before `AppConfig.ready()` runs. If we replace `admin.site` in `ready()`, existing registrations have already landed on the old default `AdminSite`.

The correct approach:

1. Replace `'django.contrib.admin'` with `'django.contrib.admin.apps.SimpleAdminConfig'` in `INSTALLED_APPS`. This suppresses Django's automatic `admin.autodiscover()` call.
2. In `AuthorizationConfig.ready()`:
   a. Import `secure_admin_site` — this triggers the `admin_site.py` module to load.
   b. Assign `admin.site = secure_admin_site` and `admin.sites.site = secure_admin_site` before any `admin.py` is imported. (Both assignments are required: one covers `from django.contrib import admin; admin.site`, the other covers `from django.contrib.admin import site`.)
   c. Call `admin.autodiscover()` manually — this now imports all app `admin.py` files, which call `admin.site.register()` against `secure_admin_site`.

This guarantees all `@admin.register`, `admin.site.register()`, and `admin.site.unregister()` calls (e.g. in `apps/audit/admin.py`) target the secured site.

Protection layers stack in order on every admin request:

```
Request → IP check → authenticated? → OIDC redirect → is_staff/superuser? → allow
```

## Components

### `apps/authorization/admin_site.py`

**`SecureAdminSite`** overrides two methods:

#### `has_permission(request)`

1. Extract client IP from `request.META['REMOTE_ADDR']`. If the deployment uses a trusted reverse proxy and `ADMIN_TRUST_PROXY = True` is set in settings, use the rightmost untrusted IP from `X-Forwarded-For` instead. The first entry in `X-Forwarded-For` is **not** used — it is client-supplied and trivially spoofable.
2. Parse `ADMIN_ALLOWED_IPS` (comma-separated IPs and CIDR ranges) into `ipaddress` network objects — parsed once at class instantiation, not per-request. Malformed CIDR entries raise `ValueError` at startup (fail fast).
3. If the allowlist is non-empty and the client IP is not in any allowed range → return `False`.
4. Delegate to `super().has_permission()` for the `is_active and is_staff` check.

When `ADMIN_ALLOWED_IPS` is empty, the IP check is skipped entirely (dev-friendly default).

#### `login(request, extra_context=None)`

Django's `AdminSite.admin_view()` calls `has_permission()` and, when it returns `False`, calls `login()`. The override:

- If the user is **not authenticated** (both GET and POST requests) → redirect to `reverse('oidc_authentication_init') + '?' + urlencode({'next': request.get_full_path()})` (using `urllib.parse.urlencode`). Using `get_full_path()` preserves query strings on admin pages (e.g. search filters); using `urlencode` ensures the `next` value is correctly percent-encoded. This prevents POST requests from reaching the underlying username/password form-processing path. Note: `login()` is called both from `AdminSite.admin_view()` (when `has_permission()` returns `False`) and directly via the explicit `/<ADMIN_URL>/login/` URL — the override covers both entry points.
- If the user is authenticated but `has_permission()` returned `False` (e.g. wrong IP, non-staff) → call `super().login()` which renders Django's built-in permission-denied page. No username/password form is shown to already-authenticated users.

### `apps/authorization/apps.py`

In `AuthorizationConfig.ready()`:

```python
from django.contrib import admin
from .admin_site import secure_admin_site

# Replace default site BEFORE autodiscover so all registrations land on the secured site.
# Both assignments are required: one for `from django.contrib import admin; admin.site`,
# one for `from django.contrib.admin import site`.
admin.site = secure_admin_site
admin.sites.site = secure_admin_site

admin.autodiscover()
```

### `config/settings.py`

Replace `'django.contrib.admin'` with `'django.contrib.admin.apps.SimpleAdminConfig'` in `INSTALLED_APPS` to suppress automatic autodiscovery:

```python
INSTALLED_APPS = [
    'django.contrib.admin.apps.SimpleAdminConfig',  # replaces 'django.contrib.admin'
    ...
]
```

- `ADMIN_URL`: URL path segment for the admin (e.g. `mgmt-a3f9c2`). Defaults to `admin` so local dev requires no extra configuration.
- `ADMIN_ALLOWED_IPS`: Comma-separated IPs and CIDR ranges (e.g. `10.0.0.0/8,192.168.1.50`). Empty string disables IP restriction.
- `ADMIN_TRUST_PROXY`: Set to `True` only when the app runs behind a trusted reverse proxy that appends to `X-Forwarded-For`. Defaults to `False` — uses `REMOTE_ADDR` only.

Update `SERVICE_AUTH_EXEMPT_URLS` in `settings.py` to use the dynamic admin path. `ADMIN_URL` must be defined **before** `SERVICE_AUTH_EXEMPT_URLS` in the file — the f-string references it at module load time and will raise `NameError` if the order is reversed. Place both settings together:

```python
# Admin endpoint configuration (must come before SERVICE_AUTH_EXEMPT_URLS)
ADMIN_URL = os.getenv('ADMIN_URL', 'admin')
ADMIN_ALLOWED_IPS = os.getenv('ADMIN_ALLOWED_IPS', '')
ADMIN_TRUST_PROXY = os.getenv('ADMIN_TRUST_PROXY', 'False').lower() in ('true', '1', 'yes')

SERVICE_AUTH_EXEMPT_URLS = [
    "/oidc/",
    f"/{ADMIN_URL}/",
    "/static/",
    "/health/",
    "/auth/",
    "/accounts/",
]
```

> **Note:** `SERVICE_AUTH_EXEMPT_URLS` must be updated in `settings.py`, not just as a fallback default in `middleware.py`. The middleware does `getattr(settings, "SERVICE_AUTH_EXEMPT_URLS", [...])` — if the setting exists in `settings.py`, the fallback default in middleware is never reached.

> **Note on `SERVICE_AUTH_EXEMPT_APPS`:** The existing `SERVICE_AUTH_EXEMPT_APPS` setting contains the string `"admin"`. This value refers to Django admin's **URL namespace** (`app_name = "admin"` in Django's admin URL config), not the URL path. It does not need to change when `ADMIN_URL` changes. Leave it as-is.

> **Why the admin prefix must stay in `SERVICE_AUTH_EXEMPT_URLS`:** Keeping the admin prefix exempt from `ServiceAccessMiddleware` is intentional and required. If it were removed, `ServiceAccessMiddleware` would attempt to resolve the admin URL to a Django app namespace and apply group-based service checks before `SecureAdminSite` could respond. Protection for admin is wholly delegated to `SecureAdminSite.has_permission()` and `login()` — the middleware must not interfere with that path.

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

The old `/admin/` path is no longer registered, so it returns 404.

## Data Flow

```
Unauthenticated GET/POST to /<ADMIN_URL>/
  → SecureAdminSite.login()
  → redirect to /oidc/authenticate/?next=/<ADMIN_URL>/...

Authenticated request, client IP not in allowlist
  → SecureAdminSite.has_permission() → False
  → login() → permission-denied page (no username/password form)

Authenticated request, IP allowed, is_staff=False
  → SecureAdminSite.has_permission() → False (super() returns False)
  → login() → permission-denied page

Authenticated request, IP allowed, is_staff=True
  → SecureAdminSite.has_permission() → True
  → admin rendered normally
```

## Error Handling

- Malformed CIDR in `ADMIN_ALLOWED_IPS` → raise `ValueError` at startup (fail fast, not silently).
- When `ADMIN_TRUST_PROXY = False` (default), `REMOTE_ADDR` is always used — no header parsing, no spoofing vector.
- When `ADMIN_TRUST_PROXY = True`, use the rightmost untrusted IP in `X-Forwarded-For` (i.e. the IP appended by the trusted proxy), not the leftmost client-supplied entry.

## Testing

File: `apps/authorization/tests/test_admin_site.py`

| Scenario | Expected |
|---|---|
| Unauthenticated GET hits admin URL | Redirect to `/oidc/authenticate/?next=...` |
| Unauthenticated POST hits admin URL | Redirect to `/oidc/authenticate/?next=...` (no form processing) |
| Authenticated non-staff user, IP allowed | Permission-denied page (no username/password form shown) |
| Authenticated staff user, IP not in allowlist | Permission-denied page |
| Authenticated staff user, IP in allowlist | 200 |
| Authenticated superuser, IP not in allowlist | Permission-denied page |
| Authenticated superuser, IP in allowlist | 200 |
| `ADMIN_ALLOWED_IPS` empty | IP check skipped; staff/superuser allowed |
| CIDR range match (`192.168.1.0/24`, client `192.168.1.50`) | 200 |
| `ADMIN_TRUST_PROXY = False` + `X-Forwarded-For` header present | `REMOTE_ADDR` used, header ignored |
| `ADMIN_TRUST_PROXY = True` + `X-Forwarded-For` set | Rightmost untrusted IP used |
| Admin URL changed via `ADMIN_URL` env var | Old `/admin/` returns 404, new URL works |
| Malformed CIDR in `ADMIN_ALLOWED_IPS` | `ValueError` raised at startup |
| OIDC redirect preserves `?next=` | After login, user lands at intended admin page |
| Existing `@admin.register` models (e.g. audit app) | All models registered on `secure_admin_site`, not default site |

## Out of Scope

- Rate limiting or brute-force protection on the admin (separate concern).
- Audit logging of admin access attempts (can be added as a follow-up via the existing audit app).
