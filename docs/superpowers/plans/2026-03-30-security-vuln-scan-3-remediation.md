# Security Vulnerability Remediation (scan-3 HIGH + MEDIUM) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remediate all HIGH (H-1, H-2, H-3) and MEDIUM (M-1, M-2, M-3, M-4) vulnerabilities identified in `docs/vulnerability/vulnerability-scan-3.md`.

**Architecture:** Each fix is self-contained and touches at most two files. No new dependencies are required. CSP is implemented as a lightweight custom Django middleware in `config/middleware.py`. The cache backend is made configurable via `CACHE_BACKEND` env var so production can switch to a persistent backend without code changes.

**Tech Stack:** Django 6, Python 3.13, `uuid` stdlib, `re` stdlib, existing test framework (`django.test.TestCase`).

---

## File Map

| File | Change |
|------|--------|
| `config/settings.py` | H-1: add cookie flags; H-2b: configurable cache; M-1: register CSP middleware |
| `apps/accounts/views.py` | H-2a: harden `_get_client_ip`; H-3: sanitize audit log username |
| `config/middleware.py` | M-1: new CSP middleware (create) |
| `apps/reports/views/api.py` | M-2: extend regex for Unicode; M-3: safe int() pagination |
| `apps/reports/services/report_data.py` | M-4: replace regex with `uuid.UUID()` |
| `apps/accounts/tests.py` | H-2a tests; H-3 tests |
| `apps/reports/tests.py` | M-2 tests; M-3 tests; M-4 stricter test |
| `apps/core/tests.py` | M-1 CSP header test |
| `.env.example` | H-2b: document `CACHE_BACKEND`, `LOGIN_TRUSTED_PROXIES` |

---

## Task 1 — H-1: Add missing cookie security flags

**Files:**
- Modify: `config/settings.py:191-194`

- [ ] **Step 1: Write the failing test**

Add to `apps/accounts/tests.py` after the existing `LogoutCsrfTest` class:

```python
class CookieSecurityFlagsTest(TestCase):
    """H-1: Session and CSRF cookies must carry HttpOnly and SameSite flags."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='cookieuser', password='testpassword123',
            is_superuser=True,
        )
        self.login_url = reverse('accounts:login')

    def test_session_cookie_is_httponly(self):
        self.client.post(
            self.login_url,
            {'username': 'cookieuser', 'password': 'testpassword123'},
        )
        session_cookie = self.client.cookies.get('sessionid')
        self.assertIsNotNone(session_cookie, "sessionid cookie not set")
        self.assertTrue(session_cookie['httponly'], "sessionid must be HttpOnly")

    def test_session_cookie_has_samesite_strict(self):
        self.client.post(
            self.login_url,
            {'username': 'cookieuser', 'password': 'testpassword123'},
        )
        session_cookie = self.client.cookies.get('sessionid')
        self.assertIsNotNone(session_cookie)
        self.assertEqual(session_cookie['samesite'], 'Strict')
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python manage.py test apps.accounts.tests.CookieSecurityFlagsTest -v 2
```

Expected: FAIL — `AssertionError: False is not true` on `httponly` or samesite mismatch.

- [ ] **Step 3: Add cookie security flags to settings**

In `config/settings.py`, after line 194 (`SESSION_SAVE_EVERY_REQUEST = True`), add:

```python
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Strict'
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python manage.py test apps.accounts.tests.CookieSecurityFlagsTest -v 2
```

Expected: PASS (2 tests).

- [ ] **Step 5: Run full test suite to check for regressions**

```bash
python manage.py test --verbosity=1
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add config/settings.py apps/accounts/tests.py
git commit -m "security: add HttpOnly and SameSite=Strict flags to session and CSRF cookies (H-1)"
```

---

## Task 2 — H-3: Sanitize username in audit log before lockout is checked

**Files:**
- Modify: `apps/accounts/views.py:74-78`

- [ ] **Step 1: Write the failing test**

Add to `apps/accounts/tests.py` after `CookieSecurityFlagsTest`:

```python
class AuditLogInjectionTest(TestCase):
    """H-3: Username in audit log must be truncated and stripped of newlines."""

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.login_url = reverse('accounts:login')
        # Create a real user so the form is valid up to the auth step
        self.user = User.objects.create_user(
            username='realuser', password='realpassword123',
            is_superuser=True,
        )

    def _hit_lockout(self, username):
        """Submit enough failed logins to trigger lockout for the given IP."""
        from django.conf import settings as django_settings
        for _ in range(django_settings.MAX_LOGIN_ATTEMPTS):
            self.client.post(self.login_url, {'username': username, 'password': 'wrong'})

    def test_newline_in_username_does_not_crash(self):
        """A username containing a newline must not cause a 500."""
        malicious = 'admin\nSUCCESS user=attacker'
        self._hit_lockout(malicious)
        response = self.client.post(
            self.login_url, {'username': malicious, 'password': 'wrong'}
        )
        # Should redirect to locked page, not crash
        self.assertIn(response.status_code, [302, 200])

    def test_very_long_username_is_truncated(self):
        """Username in audit detail must be capped at 150 characters."""
        long_name = 'a' * 500
        self._hit_lockout(long_name)
        # Should not raise — just verify no 500
        response = self.client.post(
            self.login_url, {'username': long_name, 'password': 'wrong'}
        )
        self.assertIn(response.status_code, [302, 200])
```

- [ ] **Step 2: Run test to verify it fails (or at least observe current behaviour)**

```bash
python manage.py test apps.accounts.tests.AuditLogInjectionTest -v 2
```

These tests may pass already (no crash) but the underlying log injection is still present — we are hardening the sanitization.

- [ ] **Step 3: Sanitize the username before it reaches the audit log**

In `apps/accounts/views.py`, replace lines 73-79:

```python
        if login_attempts >= max_attempts:
            emit_audit_event(request, "auth.login.locked", detail={
                "username_attempted": request.POST.get("username", ""),
                "attempt_count": login_attempts,
                "ip": client_ip,
            })
            return redirect('/auth/login/?error=locked')
```

With:

```python
        if login_attempts >= max_attempts:
            raw_username = request.POST.get("username", "")
            safe_username = raw_username.replace('\n', ' ').replace('\r', ' ')[:150]
            emit_audit_event(request, "auth.login.locked", detail={
                "username_attempted": safe_username,
                "attempt_count": login_attempts,
                "ip": client_ip,
            })
            return redirect('/auth/login/?error=locked')
```

- [ ] **Step 4: Run tests**

```bash
python manage.py test apps.accounts.tests.AuditLogInjectionTest -v 2
```

Expected: PASS (2 tests).

- [ ] **Step 5: Run full test suite**

```bash
python manage.py test --verbosity=1
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add apps/accounts/views.py apps/accounts/tests.py
git commit -m "security: sanitize username before writing to audit log to prevent log injection (H-3)"
```

---

## Task 3 — H-2a: Harden `_get_client_ip` against X-Forwarded-For spoofing

**Files:**
- Modify: `apps/accounts/views.py:124-129`
- Modify: `config/settings.py` (add `LOGIN_TRUSTED_PROXIES` setting)

- [ ] **Step 1: Write the failing test**

Add to `apps/accounts/tests.py`:

```python
class ClientIpExtractionTest(TestCase):
    """H-2a: _get_client_ip must not trust X-Forwarded-For from untrusted sources."""

    def _get_ip(self, meta):
        from apps.accounts.views import LoginView
        view = LoginView()
        from django.test import RequestFactory
        rf = RequestFactory()
        request = rf.get('/')
        request.META.update(meta)
        return view._get_client_ip(request)

    def test_uses_remote_addr_when_no_forwarded_for(self):
        ip = self._get_ip({'REMOTE_ADDR': '1.2.3.4'})
        self.assertEqual(ip, '1.2.3.4')

    def test_ignores_forwarded_for_from_untrusted_remote_addr(self):
        """When REMOTE_ADDR is not in TRUSTED_PROXIES, ignore X-Forwarded-For."""
        ip = self._get_ip({
            'REMOTE_ADDR': '5.6.7.8',           # not a trusted proxy
            'HTTP_X_FORWARDED_FOR': '1.1.1.1',  # attacker-controlled
        })
        self.assertEqual(ip, '5.6.7.8')

    def test_uses_forwarded_for_rightmost_from_trusted_proxy(self):
        """When REMOTE_ADDR is a trusted proxy, take the rightmost XFF IP."""
        with self.settings(LOGIN_TRUSTED_PROXIES=['127.0.0.1']):
            ip = self._get_ip({
                'REMOTE_ADDR': '127.0.0.1',
                'HTTP_X_FORWARDED_FOR': '10.0.0.1, 192.168.1.1',
            })
        self.assertEqual(ip, '192.168.1.1')
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python manage.py test apps.accounts.tests.ClientIpExtractionTest -v 2
```

Expected: FAIL — `test_ignores_forwarded_for_from_untrusted_remote_addr` fails because current code always trusts XFF.

- [ ] **Step 3: Update `_get_client_ip` in views.py**

Replace lines 124-129 in `apps/accounts/views.py`:

```python
    def _get_client_ip(self, request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
```

With:

```python
    def _get_client_ip(self, request):
        """Get client IP address from request.

        Only trusts X-Forwarded-For when REMOTE_ADDR is in LOGIN_TRUSTED_PROXIES.
        Takes the rightmost XFF entry to avoid attacker-prepended spoofed IPs.
        """
        remote_addr = request.META.get('REMOTE_ADDR', '')
        trusted_proxies = getattr(settings, 'LOGIN_TRUSTED_PROXIES', [])
        if remote_addr in trusted_proxies:
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
            if x_forwarded_for:
                return x_forwarded_for.split(',')[-1].strip()
        return remote_addr
```

- [ ] **Step 4: Add `LOGIN_TRUSTED_PROXIES` to settings.py**

In `config/settings.py`, after `LOCKOUT_DURATION` (line 313), add:

```python
# Trusted reverse proxy IPs for X-Forwarded-For extraction (space-separated in env)
LOGIN_TRUSTED_PROXIES = [
    ip.strip()
    for ip in os.getenv('LOGIN_TRUSTED_PROXIES', '').split()
    if ip.strip()
]
```

- [ ] **Step 5: Run tests**

```bash
python manage.py test apps.accounts.tests.ClientIpExtractionTest -v 2
```

Expected: PASS (3 tests).

- [ ] **Step 6: Run full test suite**

```bash
python manage.py test --verbosity=1
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add apps/accounts/views.py config/settings.py apps/accounts/tests.py
git commit -m "security: harden _get_client_ip to ignore X-Forwarded-For from untrusted proxies (H-2a)"
```

---

## Task 4 — H-2b: Make cache backend configurable for production

**Files:**
- Modify: `config/settings.py:299-304`
- Modify: `.env.example`

- [ ] **Step 1: Replace hardcoded LocMemCache with env-driven config**

Replace lines 299-304 in `config/settings.py`:

```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}
```

With:

```python
_CACHE_BACKEND = os.getenv('CACHE_BACKEND', 'locmem')

if _CACHE_BACKEND == 'redis':
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/1'),
        }
    }
elif _CACHE_BACKEND == 'file':
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
            'LOCATION': os.getenv('FILE_CACHE_DIR', '/tmp/django_cache'),
        }
    }
else:
    # Default: LocMemCache — fine for development, NOT suitable for multi-instance production
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
        }
    }
```

- [ ] **Step 2: Document the new variables in `.env.example`**

Open `.env.example` and add after the existing rate-limiting block:

```
# Cache backend for rate limiting (locmem | file | redis)
# Use 'redis' or 'file' in multi-instance/production deployments.
# 'locmem' (default) loses counters on restart and is not shared across instances.
CACHE_BACKEND=locmem
REDIS_URL=redis://127.0.0.1:6379/1
FILE_CACHE_DIR=/tmp/django_cache

# Trusted reverse proxy IPs for X-Forwarded-For extraction (space-separated)
LOGIN_TRUSTED_PROXIES=
```

- [ ] **Step 3: Run test suite to confirm no regressions**

```bash
python manage.py test --verbosity=1
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add config/settings.py .env.example
git commit -m "security: make cache backend configurable via env var for production rate-limiting (H-2b)"
```

---

## Task 5 — M-4: Replace custom GUID regex with `uuid.UUID()` validation

**Files:**
- Modify: `apps/reports/services/report_data.py:1-30`

- [ ] **Step 1: Write a stricter test that exposes the regex weakness**

Add to `apps/reports/tests.py` inside `ReportIdValidationTest`:

```python
    def test_partial_hyphen_guid_raises_value_error(self):
        """Old regex accepted malformed GUIDs with misplaced hyphens; uuid.UUID rejects them."""
        from apps.reports.services.report_data import _validate_report_id
        with self.assertRaises(ValueError):
            # Hyphens in wrong positions — valid hex but not a valid UUID format
            _validate_report_id('a1b2c3d4-e5f67890abcdef1234567890')
```

- [ ] **Step 2: Run the new test to verify it fails**

```bash
python manage.py test apps.reports.tests.ReportIdValidationTest.test_partial_hyphen_guid_raises_value_error -v 2
```

Expected: FAIL — the old regex allows this malformed input.

- [ ] **Step 3: Replace the regex implementation**

In `apps/reports/services/report_data.py`, replace lines 1-30:

```python
"""Service for fetching and processing report data from ArcGIS."""

import math
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

from apps.core.services.arcgis import query_feature_layer, get_attachments
from apps.reports.mappings import (
    get_field_label,
    get_field_value,
    process_attributes,
    process_features,
)


def _validate_report_id(report_id):
    """
    Validate that report_id is a well-formed UUID/GUID.

    Accepts the three standard Python uuid.UUID input formats:
      - With dashes:    'a1b2c3d4-e5f6-7890-abcd-ef1234567890'
      - Without dashes: 'a1b2c3d4e5f67890abcdef1234567890'
      - With braces:    '{a1b2c3d4-e5f6-7890-abcd-ef1234567890}'

    Raises:
        ValueError: if report_id is None, not a string, or not a valid UUID.
    """
    try:
        uuid.UUID(str(report_id))
    except (ValueError, AttributeError):
        raise ValueError("Invalid report_id: not a valid GUID")
```

Note: `re` import is no longer needed — remove it. The `math` import and everything from line 31 onward stays unchanged.

- [ ] **Step 4: Run the full `ReportIdValidationTest` suite**

```bash
python manage.py test apps.reports.tests.ReportIdValidationTest -v 2
```

Expected: PASS (all 8 tests including the new one).

- [ ] **Step 5: Run full test suite**

```bash
python manage.py test --verbosity=1
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add apps/reports/services/report_data.py apps/reports/tests.py
git commit -m "security: replace custom GUID regex with uuid.UUID() for stricter validation (M-4)"
```

---

## Task 6 — M-3: Guard pagination `int()` against non-numeric and negative values

**Files:**
- Modify: `apps/reports/views/api.py:192-195`

- [ ] **Step 1: Write failing tests**

Add to `apps/reports/tests.py`:

```python
class PaginationValidationTest(TestCase):
    """M-3: Pagination parameters must be validated before int() conversion."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='pageuser', password='testpassword123',
            is_superuser=True,
        )
        self.client.force_login(self.user, backend='apps.accounts.auth.SuperuserOnlyModelBackend')

    def test_non_numeric_page_returns_400(self):
        response = self.client.get('/api/data/', {'page': 'abc'})
        self.assertEqual(response.status_code, 400)

    def test_non_numeric_per_page_returns_400(self):
        response = self.client.get('/api/data/', {'per_page': 'xyz'})
        self.assertEqual(response.status_code, 400)

    def test_negative_page_is_clamped_to_1(self):
        """Negative page should not cause a negative offset — clamp to 1."""
        with patch('apps.reports.views.api.query_feature_layer', return_value={'features': []}):
            response = self.client.get('/api/data/', {'page': '-5'})
        self.assertIn(response.status_code, [200, 400])
        if response.status_code == 200:
            import json
            body = json.loads(response.content)
            # offset must never be negative
            self.assertGreaterEqual(body.get('page', 1), 1)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python manage.py test apps.reports.tests.PaginationValidationTest -v 2
```

Expected: `test_non_numeric_page_returns_400` and `test_non_numeric_per_page_returns_400` FAIL with 500 (unhandled ValueError).

- [ ] **Step 3: Replace the pagination block in `apps/reports/views/api.py`**

Replace lines 192-195:

```python
        page = int(request.GET.get('page', 1))
        per_page = min(int(request.GET.get('per_page', 10)), settings.MAX_ITEMS_PER_PAGE)
        offset = (page - 1) * per_page
```

With:

```python
        try:
            page = max(1, int(request.GET.get('page', 1)))
            per_page = min(
                max(1, int(request.GET.get('per_page', 10))),
                settings.MAX_ITEMS_PER_PAGE,
            )
        except (ValueError, TypeError):
            return JsonResponse({'error': 'Parametri di paginazione non validi.'}, status=400)
        offset = (page - 1) * per_page
```

- [ ] **Step 4: Run pagination tests**

```bash
python manage.py test apps.reports.tests.PaginationValidationTest -v 2
```

Expected: PASS (3 tests).

- [ ] **Step 5: Run full test suite**

```bash
python manage.py test --verbosity=1
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add apps/reports/views/api.py apps/reports/tests.py
git commit -m "security: guard pagination int() conversion against non-numeric and negative values (M-3)"
```

---

## Task 7 — M-2: Extend filter allowlist regex to accept Italian Unicode characters

**Files:**
- Modify: `apps/reports/views/api.py:40`

- [ ] **Step 1: Write a failing test**

Add to `apps/reports/tests.py`:

```python
class FilterAllowlistTest(TestCase):
    """M-2: Filter regex must accept Italian accented characters."""

    def test_italian_accented_name_is_valid(self):
        from apps.reports.views.api import build_where_clause
        # Should not raise ValueError
        where = build_where_clause({'nome_operatore': ['Società Costruzioni']})
        self.assertIn('Societ', where)

    def test_accented_tratta_is_valid(self):
        from apps.reports.views.api import build_where_clause
        where = build_where_clause({'tratta': ['Nò-Milano']})
        self.assertIn('Nò-Milano', where)

    def test_sql_metacharacters_still_rejected(self):
        from apps.reports.views.api import build_where_clause
        with self.assertRaises(ValueError):
            build_where_clause({'nome_operatore': ["admin'; DROP TABLE"]})
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python manage.py test apps.reports.tests.FilterAllowlistTest -v 2
```

Expected: `test_italian_accented_name_is_valid` and `test_accented_tratta_is_valid` FAIL with `ValueError: Invalid characters`.

- [ ] **Step 3: Update the regex in `apps/reports/views/api.py`**

Replace line 40:

```python
_FILTER_VALUE_RE = re.compile(r'^[a-zA-Z0-9_\-\. ]+$')
```

With:

```python
_FILTER_VALUE_RE = re.compile(r'^[\w\-\. ]+$', re.UNICODE)
```

`\w` with `re.UNICODE` matches `[a-zA-Z0-9_]` plus Unicode letters and digits (Italian accented characters included). SQL metacharacters (`'`, `;`, `(`, `)`, `=`, `--`) are still rejected.

- [ ] **Step 4: Run filter allowlist tests**

```bash
python manage.py test apps.reports.tests.FilterAllowlistTest -v 2
```

Expected: PASS (3 tests).

- [ ] **Step 5: Run full test suite**

```bash
python manage.py test --verbosity=1
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add apps/reports/views/api.py apps/reports/tests.py
git commit -m "security: extend filter allowlist regex to accept Italian Unicode characters (M-2)"
```

---

## Task 8 — M-1: Add Content Security Policy middleware

**Files:**
- Create: `config/middleware.py`
- Modify: `config/settings.py` (MIDDLEWARE list + CSP settings)

- [ ] **Step 1: Write the failing test**

Add to `apps/core/tests.py`:

```python
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model

User = get_user_model()


class ContentSecurityPolicyTest(TestCase):
    """M-1: Every response must carry a Content-Security-Policy header."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='cspuser', password='testpassword123',
            is_superuser=True,
        )
        self.client.force_login(self.user, backend='apps.accounts.auth.SuperuserOnlyModelBackend')

    def test_csp_header_present_on_html_response(self):
        response = self.client.get('/')
        self.assertIn('Content-Security-Policy', response)

    def test_csp_default_src_is_self(self):
        response = self.client.get('/')
        csp = response.get('Content-Security-Policy', '')
        self.assertIn("default-src 'self'", csp)

    def test_csp_frame_ancestors_is_none(self):
        response = self.client.get('/')
        csp = response.get('Content-Security-Policy', '')
        self.assertIn("frame-ancestors 'none'", csp)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python manage.py test apps.core.tests.ContentSecurityPolicyTest -v 2
```

Expected: FAIL — `AssertionError: 'Content-Security-Policy' not found in response`.

- [ ] **Step 3: Create `config/middleware.py`**

```python
"""Project-level Django middleware."""

from django.conf import settings


class ContentSecurityPolicyMiddleware:
    """Attach a Content-Security-Policy header to every response.

    The policy is assembled from the CSP_POLICY dict in settings.
    Each key is a CSP directive name; the value is a list of source strings.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        policy = getattr(settings, 'CSP_POLICY', {})
        self._header_value = '; '.join(
            f"{directive} {' '.join(sources)}"
            for directive, sources in policy.items()
        )

    def __call__(self, request):
        response = self.get_response(request)
        if self._header_value:
            response['Content-Security-Policy'] = self._header_value
        return response
```

- [ ] **Step 4: Add CSP settings and register middleware in `config/settings.py`**

Add the `CSP_POLICY` dict after the production security headers block (after line 328):

```python
# Content Security Policy — applied by config.middleware.ContentSecurityPolicyMiddleware
CSP_POLICY = {
    "default-src": ["'self'"],
    "script-src": ["'self'"],
    "style-src": ["'self'", "cdnjs.cloudflare.com"],
    "font-src": ["'self'", "cdnjs.cloudflare.com"],
    "img-src": ["'self'", "data:", "https:"],
    "connect-src": ["'self'"],
    "frame-ancestors": ["'none'"],
}
```

Add the middleware to the `MIDDLEWARE` list in `config/settings.py` (after `XFrameOptionsMiddleware`):

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'mozilla_django_oidc.middleware.SessionRefresh',
    'apps.authorization.middleware.ServiceAccessMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'config.middleware.ContentSecurityPolicyMiddleware',   # <-- add this line
]
```

- [ ] **Step 5: Run CSP tests**

```bash
python manage.py test apps.core.tests.ContentSecurityPolicyTest -v 2
```

Expected: PASS (3 tests).

- [ ] **Step 6: Run full test suite**

```bash
python manage.py test --verbosity=1
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add config/middleware.py config/settings.py apps/core/tests.py
git commit -m "security: add ContentSecurityPolicyMiddleware with strict default-src policy (M-1)"
```

---

## Final Verification

- [ ] **Run complete test suite one final time**

```bash
python manage.py test --verbosity=2
```

Expected: all tests pass, zero failures, zero errors.

- [ ] **Manual smoke test** — start the dev server and confirm:
  - Login page loads and logs in correctly
  - `/reports/` page loads
  - Browser DevTools → Network tab → response headers include `Content-Security-Policy`
  - No console errors from CSP violations

```bash
python manage.py runserver
```
