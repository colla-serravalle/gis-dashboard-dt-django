# Fix High Vulnerabilities Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve all 6 HIGH-severity security vulnerabilities identified in the vulnerability scan before production deployment.

**Architecture:** Each fix is isolated to a single file or a small group of related files. Settings hardening is grouped together; view-level fixes are each their own task. All changes follow the existing Django patterns in the codebase.

**Tech Stack:** Django 5.x, mozilla-django-oidc, Python 3.x, Django test client

---

## File Structure

| File | Change | Vulnerabilities |
|------|--------|-----------------|
| `config/settings.py` | Change DEBUG default to False; add production security-header block | H-3, H-2 |
| `apps/accounts/views.py` | Validate `next` URL before redirect; add `@require_POST` to logout | H-1, H-6 |
| `apps/accounts/tests.py` | Tests for open-redirect fix and logout CSRF fix | H-1, H-6 |
| `templates/includes/sidebar.html` | Replace `<a href="logout">` with CSRF-protected `<form>` (x2) | H-6 |
| `apps/reports/services/report_data.py` | Validate `report_id` against GUID regex before interpolation | H-4 |
| `apps/reports/views/pages.py` | Handle `ValueError` from `get_report_data` → 400 response | H-4 |
| `apps/reports/views/pdf.py` | Handle `ValueError` from `get_report_data` → 400 response | H-4 |
| `apps/reports/views/api.py` | Replace `str(e)` with generic error messages at lines 250, 328, 357 | H-5 |
| `apps/reports/tests.py` | Tests for injection validation and exception sanitization | H-4, H-5 |

---

## Task 1: Settings Hardening (H-3 + H-2)

**Files:**
- Modify: `config/settings.py:43` (DEBUG default)
- Modify: `config/settings.py` (add production security block at end of Security Settings section)

> These two changes are in the same file and require no tests — Django's `check --deploy` command verifies them.

- [ ] **Step 1: Change DEBUG default from True to False**

In `config/settings.py` line 43, change:
```python
DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 'yes')
```
to:
```python
DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 'yes')
```

- [ ] **Step 2: Add production security headers block**

In `config/settings.py`, find the `# Security Settings` section (around line 308) and append after the `LOCKOUT_DURATION` line:

```python
# Production security headers — only active when DEBUG=False
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000          # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
```

- [ ] **Step 3: Verify with Django deployment check**

Run:
```bash
python manage.py check --deploy
```
Expected: warnings about HSTS preload and SSL redirect are now gone. Any remaining warnings should be informational only (e.g., SQLite in production — that is a separate medium finding).

- [ ] **Step 4: Verify DEBUG default is False**

Run:
```bash
python -c "import django; import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings'); django.setup(); from django.conf import settings; assert not settings.DEBUG, 'DEBUG should be False by default'"
```
Expected: exits with code 0 (no assertion error).

- [ ] **Step 5: Commit**

```bash
git add config/settings.py
git commit -m "security: default DEBUG=False; add production security headers"
```

---

## Task 2: Fix Open Redirect in Login View (H-1)

**Files:**
- Modify: `apps/accounts/views.py:89-91`
- Modify: `apps/accounts/tests.py`

- [ ] **Step 1: Write failing tests**

In `apps/accounts/tests.py`, replace the entire file content with:

```python
from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class OpenRedirectTest(TestCase):
    """H-1: Open redirect via ?next= parameter must be blocked."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', password='testpassword123'
        )
        self.login_url = reverse('accounts:login')

    def test_safe_next_redirects_correctly(self):
        """A relative next= URL is honoured after login."""
        response = self.client.post(
            f'{self.login_url}?next=/reports/',
            {'username': 'testuser', 'password': 'testpassword123'},
        )
        self.assertRedirects(response, '/reports/', fetch_redirect_response=False)

    def test_absolute_external_next_falls_back_to_home(self):
        """An absolute URL pointing to another host is rejected."""
        response = self.client.post(
            f'{self.login_url}?next=https://evil.com/steal',
            {'username': 'testuser', 'password': 'testpassword123'},
        )
        self.assertRedirects(response, '/', fetch_redirect_response=False)

    def test_protocol_relative_next_falls_back_to_home(self):
        """A protocol-relative URL (//evil.com) is rejected."""
        response = self.client.post(
            f'{self.login_url}?next=//evil.com/steal',
            {'username': 'testuser', 'password': 'testpassword123'},
        )
        self.assertRedirects(response, '/', fetch_redirect_response=False)

    def test_missing_next_redirects_to_home(self):
        """Login without next= redirects to /."""
        response = self.client.post(
            self.login_url,
            {'username': 'testuser', 'password': 'testpassword123'},
        )
        self.assertRedirects(response, '/', fetch_redirect_response=False)
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python manage.py test apps.accounts.tests.OpenRedirectTest -v 2
```
Expected: `test_absolute_external_next_falls_back_to_home` and `test_protocol_relative_next_falls_back_to_home` FAIL (currently the redirect follows evil.com).

- [ ] **Step 3: Fix the open redirect in the view**

In `apps/accounts/views.py`, add the import at the top of the file alongside the existing imports:
```python
from django.utils.http import url_has_allowed_host_and_scheme
```

Then in the `post` method, replace lines 89-91:
```python
                # Redirect to next URL or home
                next_url = request.GET.get('next', '/')
                return redirect(next_url)
```
with:
```python
                # Redirect to next URL or home — reject cross-host redirects
                next_url = request.GET.get('next', '/')
                if not url_has_allowed_host_and_scheme(
                    url=next_url,
                    allowed_hosts={request.get_host()},
                    require_https=request.is_secure(),
                ):
                    next_url = '/'
                return redirect(next_url)
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
python manage.py test apps.accounts.tests.OpenRedirectTest -v 2
```
Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/accounts/views.py apps/accounts/tests.py
git commit -m "security(H-1): validate next= URL before redirect to prevent open redirect"
```

---

## Task 3: Fix Logout via GET Without CSRF (H-6)

**Files:**
- Modify: `apps/accounts/views.py:120-125`
- Modify: `templates/includes/sidebar.html` (lines 55-60 and 69-74)
- Modify: `apps/accounts/tests.py` (add logout tests)

- [ ] **Step 1: Write failing tests**

In `apps/accounts/tests.py`, append these classes after the `OpenRedirectTest` class:

```python
class LogoutCsrfTest(TestCase):
    """H-6: Logout must require POST to prevent CSRF-based force-logout."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='logoutuser', password='testpassword123'
        )
        self.logout_url = reverse('accounts:logout')

    def test_logout_get_returns_405(self):
        """GET to logout must be rejected with 405 Method Not Allowed."""
        self.client.force_login(self.user)
        response = self.client.get(self.logout_url)
        self.assertEqual(response.status_code, 405)

    def test_logout_post_without_csrf_is_rejected(self):
        """POST without CSRF token must be rejected with 403."""
        self.client.force_login(self.user)
        # enforce_csrf_checks=True simulates a real browser without a valid token
        client = self.client_class(enforce_csrf_checks=True)
        client.force_login(self.user)
        response = client.post(self.logout_url)
        self.assertEqual(response.status_code, 403)

    def test_logout_post_with_csrf_succeeds(self):
        """Valid POST with CSRF token must log the user out."""
        self.client.force_login(self.user)
        response = self.client.post(self.logout_url)
        # Should redirect to login after logout
        self.assertRedirects(response, '/auth/login/', fetch_redirect_response=False)
        # Confirm user is no longer authenticated
        self.assertFalse(response.wsgi_request.user.is_authenticated)
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python manage.py test apps.accounts.tests.LogoutCsrfTest -v 2
```
Expected: `test_logout_get_returns_405` FAILS (currently GET is accepted).

- [ ] **Step 3: Add @require_POST to logout view**

In `apps/accounts/views.py`, update the imports block to include `require_POST`:
```python
from django.views.decorators.http import require_POST
```

Then replace the `logout_view` function (lines 120-125):
```python
def logout_view(request):
    """Logout user and redirect to login page."""
    if request.user.is_authenticated:
        emit_audit_event(request, "auth.logout", detail={})
    logout(request)
    return redirect(settings.LOGIN_URL)
```
with:
```python
@require_POST
def logout_view(request):
    """Logout user and redirect to login page. Requires POST to prevent CSRF-based force-logout."""
    if request.user.is_authenticated:
        emit_audit_event(request, "auth.logout", detail={})
    logout(request)
    return redirect(settings.LOGIN_URL)
```

- [ ] **Step 4: Update sidebar template — mobile logout link**

In `templates/includes/sidebar.html`, replace lines 55-60:
```html
    <li class="logout-link mobile-only">
        <a href="{% url 'accounts:logout' %}">
            <svg xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px" fill="#e3e3e3"><path d="M200-120q-33 0-56.5-23.5T120-200v-560q0-33 23.5-56.5T200-840h280v80H200v560h280v80H200Zm440-160-55-58 102-102H360v-80h327L585-622l55-58 200 200-200 200Z"/></svg>
            <span>Logout</span>
        </a>
    </li>
```
with:
```html
    <li class="logout-link mobile-only">
        <form method="post" action="{% url 'accounts:logout' %}" style="display:contents">
            {% csrf_token %}
            <button type="submit" class="logout-btn">
                <svg xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px" fill="#e3e3e3"><path d="M200-120q-33 0-56.5-23.5T120-200v-560q0-33 23.5-56.5T200-840h280v80H200v560h280v80H200Zm440-160-55-58 102-102H360v-80h327L585-622l55-58 200 200-200 200Z"/></svg>
                <span>Logout</span>
            </button>
        </form>
    </li>
```

- [ ] **Step 5: Update sidebar template — desktop logout link**

In `templates/includes/sidebar.html`, replace lines 69-74:
```html
    <li class="logout-link desktop-only">
        <a href="{% url 'accounts:logout' %}">
            <svg xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px" fill="#e3e3e3"><path d="M200-120q-33 0-56.5-23.5T120-200v-560q0-33 23.5-56.5T200-840h280v80H200v560h280v80H200Zm440-160-55-58 102-102H360v-80h327L585-622l55-58 200 200-200 200Z"/></svg>
            <span>Logout</span>
        </a>
    </li>
```
with:
```html
    <li class="logout-link desktop-only">
        <form method="post" action="{% url 'accounts:logout' %}" style="display:contents">
            {% csrf_token %}
            <button type="submit" class="logout-btn">
                <svg xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px" fill="#e3e3e3"><path d="M200-120q-33 0-56.5-23.5T120-200v-560q0-33 23.5-56.5T200-840h280v80H200v560h280v80H200Zm440-160-55-58 102-102H360v-80h327L585-622l55-58 200 200-200 200Z"/></svg>
                <span>Logout</span>
            </button>
        </form>
    </li>
```

- [ ] **Step 6: Run tests to confirm they pass**

```bash
python manage.py test apps.accounts.tests.LogoutCsrfTest -v 2
```
Expected: all 3 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/accounts/views.py apps/accounts/tests.py templates/includes/sidebar.html
git commit -m "security(H-6): require POST for logout to prevent CSRF-based force-logout"
```

---

## Task 4: Fix ArcGIS WHERE Clause Injection (H-4)

**Files:**
- Modify: `apps/reports/services/report_data.py:15`
- Modify: `apps/reports/views/pages.py:43-49`
- Modify: `apps/reports/views/pdf.py` (wherever `get_report_data` is called)
- Modify: `apps/reports/tests.py`

- [ ] **Step 1: Write failing tests**

Open `apps/reports/tests.py` and append:

```python
from django.test import TestCase
from apps.reports.services.report_data import get_report_data


class ReportIdValidationTest(TestCase):
    """H-4: report_id must be validated as GUID before ArcGIS query."""

    def test_valid_guid_with_dashes_is_accepted(self):
        """A standard UUID-format id raises no error during validation."""
        # get_report_data will query ArcGIS and return None (no matching record)
        # rather than raising ValueError — mocked ArcGIS here would need extra setup.
        # We test the validation itself by calling the validator directly.
        from apps.reports.services.report_data import _validate_report_id
        # Should not raise
        _validate_report_id('a1b2c3d4-e5f6-7890-abcd-ef1234567890')

    def test_valid_guid_without_dashes_is_accepted(self):
        from apps.reports.services.report_data import _validate_report_id
        _validate_report_id('a1b2c3d4e5f67890abcdef1234567890')

    def test_guid_with_curly_braces_is_accepted(self):
        from apps.reports.services.report_data import _validate_report_id
        _validate_report_id('{a1b2c3d4-e5f6-7890-abcd-ef1234567890}')

    def test_sql_injection_attempt_raises_value_error(self):
        from apps.reports.services.report_data import _validate_report_id
        with self.assertRaises(ValueError):
            _validate_report_id("' OR '1'='1")

    def test_empty_string_raises_value_error(self):
        from apps.reports.services.report_data import _validate_report_id
        with self.assertRaises(ValueError):
            _validate_report_id('')

    def test_none_raises_value_error(self):
        from apps.reports.services.report_data import _validate_report_id
        with self.assertRaises(ValueError):
            _validate_report_id(None)

    def test_path_traversal_raises_value_error(self):
        from apps.reports.services.report_data import _validate_report_id
        with self.assertRaises(ValueError):
            _validate_report_id('../../../etc/passwd')


class ReportDetailViewValidationTest(TestCase):
    """H-4: ReportDetailView rejects invalid report IDs with 400."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.user = User.objects.create_user(
            username='reportuser', password='testpassword123'
        )
        self.client.force_login(self.user)

    def test_invalid_report_id_returns_400(self):
        response = self.client.get('/reports/detail/?id=' + "' OR 1=1 --")
        self.assertEqual(response.status_code, 400)

    def test_missing_report_id_redirects(self):
        response = self.client.get('/reports/detail/')
        self.assertEqual(response.status_code, 302)
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python manage.py test apps.reports.tests.ReportIdValidationTest apps.reports.tests.ReportDetailViewValidationTest -v 2
```
Expected: all tests FAIL because `_validate_report_id` does not exist yet.

- [ ] **Step 3: Add validation function to report_data.py**

In `apps/reports/services/report_data.py`, add at the top after the existing imports:

```python
import re

_GUID_RE = re.compile(
    r'^[{]?[0-9a-fA-F]{8}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{12}[}]?$'
)


def _validate_report_id(report_id):
    """
    Validate that report_id matches a GUID/UUID pattern.

    Raises:
        ValueError: if report_id is None, empty, or not a valid GUID.
    """
    if not report_id or not isinstance(report_id, str):
        raise ValueError(f"Invalid report_id: {report_id!r}")
    if not _GUID_RE.match(report_id):
        raise ValueError(f"Invalid report_id format: {report_id!r}")
```

Then at the start of `get_report_data`, add the validation call:

```python
def get_report_data(report_id):
    """
    Fetch and process all data for a report.

    Args:
        report_id: The uniquerowid of the report. Must be a valid GUID.

    Returns:
        dict with all processed report data, or None if the main record is not found.

    Raises:
        ValueError: if report_id is not a valid GUID format.
    """
    _validate_report_id(report_id)

    # Query main record first (needed to validate existence)
    main = query_feature_layer(0, f"uniquerowid='{report_id}'")
    ...  # rest of function unchanged
```

- [ ] **Step 4: Handle ValueError in ReportDetailView**

In `apps/reports/views/pages.py`, update the `get` method of `ReportDetailView`:

```python
    def get(self, request):
        report_id = request.GET.get('id')

        if not report_id:
            return redirect('reports:report_list')

        try:
            data = get_report_data(report_id)
        except ValueError:
            from django.http import HttpResponseBadRequest
            return HttpResponseBadRequest('ID report non valido.')

        if data is None:
            return render(request, self.template_name, {
                'error': 'Record non trovato'
            })

        emit_audit_event(request, "data.report.viewed", detail={"report_id": report_id})
        return render(request, self.template_name, data)
```

- [ ] **Step 5: Handle ValueError in pdf view**

Open `apps/reports/views/pdf.py` and read the current `get_report_data` call. Wrap it in a try/except:

```python
        try:
            data = get_report_data(report_id)
        except ValueError:
            from django.http import HttpResponseBadRequest
            return HttpResponseBadRequest('ID report non valido.')
```

- [ ] **Step 6: Run tests to confirm they pass**

```bash
python manage.py test apps.reports.tests.ReportIdValidationTest apps.reports.tests.ReportDetailViewValidationTest -v 2
```
Expected: all tests PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/reports/services/report_data.py apps/reports/views/pages.py apps/reports/views/pdf.py apps/reports/tests.py
git commit -m "security(H-4): validate report_id as GUID before ArcGIS WHERE clause interpolation"
```

---

## Task 5: Sanitize Exception Details Leaked to Clients (H-5)

**Files:**
- Modify: `apps/reports/views/api.py:250,328,357`
- Modify: `apps/reports/tests.py`

- [ ] **Step 1: Write failing tests**

In `apps/reports/tests.py`, append:

```python
from unittest.mock import patch
from django.test import TestCase


class ExceptionSanitizationTest(TestCase):
    """H-5: Exception details must not be returned in API responses."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.user = User.objects.create_user(
            username='apiuser', password='testpassword123'
        )
        self.client.force_login(self.user)

    def test_get_data_500_returns_generic_message(self):
        """Internal exception in get_data must not expose str(e) to client."""
        with patch('apps.reports.views.api.query_feature_layer', side_effect=RuntimeError('secret db connection string')):
            response = self.client.get('/reports/api/data/')
        self.assertEqual(response.status_code, 500)
        import json
        body = json.loads(response.content)
        self.assertNotIn('secret db connection string', body.get('error', ''))
        self.assertIn('error', body)

    def test_get_filter_options_500_returns_generic_message(self):
        """Internal exception in get_filter_options must not expose str(e) to client."""
        with patch('apps.reports.views.api.query_feature_layer', side_effect=RuntimeError('secret db connection string')):
            response = self.client.get('/reports/api/filter-options/')
        self.assertEqual(response.status_code, 500)
        import json
        body = json.loads(response.content)
        self.assertNotIn('secret db connection string', body.get('error', ''))

    def test_image_proxy_500_returns_generic_message(self):
        """Internal exception in image_proxy must not expose str(e) to client."""
        with patch('apps.reports.views.api.get_arcgis_service', side_effect=RuntimeError('secret arcgis token')):
            response = self.client.get('/reports/api/image/0/1/1/')
        self.assertEqual(response.status_code, 500)
        self.assertNotIn(b'secret arcgis token', response.content)
```

- [ ] **Step 2: Check the URL patterns to use in tests**

Run:
```bash
python manage.py show_urls 2>/dev/null | grep "reports/api" || python manage.py shell -c "from django.urls import reverse; print(reverse('reports:get_data'))"
```
If the URL names differ from what is used in the tests above, update the test URLs accordingly.

- [ ] **Step 3: Run tests to confirm they fail**

```bash
python manage.py test apps.reports.tests.ExceptionSanitizationTest -v 2
```
Expected: tests FAIL because current code returns `str(e)` which contains the secret message.

- [ ] **Step 4: Replace str(e) in api.py**

In `apps/reports/views/api.py`:

**Line 248-250** (inside `get_data` except block), replace:
```python
    except Exception as e:
        logger.exception("Error in get_data")
        return JsonResponse({'error': str(e)}, status=500)
```
with:
```python
    except Exception:
        logger.exception("Error in get_data")
        return JsonResponse({'error': 'Si è verificato un errore interno.'}, status=500)
```

**Line 326-328** (inside `get_filter_options` except block), replace:
```python
    except Exception as e:
        logger.exception("Error in get_filter_options")
        return JsonResponse({'error': str(e)}, status=500)
```
with:
```python
    except Exception:
        logger.exception("Error in get_filter_options")
        return JsonResponse({'error': 'Si è verificato un errore interno.'}, status=500)
```

**Line 355-357** (inside `image_proxy` except block), replace:
```python
    except Exception as e:
        logger.exception("Error in image_proxy")
        return HttpResponse(f"Errore: {str(e)}", status=500)
```
with:
```python
    except Exception:
        logger.exception("Error in image_proxy")
        return HttpResponse("Si è verificato un errore interno.", status=500)
```

- [ ] **Step 5: Run tests to confirm they pass**

```bash
python manage.py test apps.reports.tests.ExceptionSanitizationTest -v 2
```
Expected: all 3 tests PASS.

- [ ] **Step 6: Run full test suite**

```bash
python manage.py test -v 2
```
Expected: all tests PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/reports/views/api.py apps/reports/tests.py
git commit -m "security(H-5): return generic error messages instead of raw exception details"
```

---

## Self-Review

### Spec coverage
- H-1 Open Redirect → Task 2 ✅
- H-2 Security Headers → Task 1 ✅
- H-3 DEBUG default → Task 1 ✅
- H-4 ArcGIS injection → Task 4 ✅
- H-5 Exception leak → Task 5 ✅
- H-6 Logout CSRF → Task 3 ✅

### Placeholder scan
- All code blocks are complete with actual implementations.
- No TBD or TODO markers.
- All type/function names used in tests (`_validate_report_id`, `get_report_data`) are defined in the same task.

### Type consistency
- `_validate_report_id` defined in Task 4 Step 3, used in Task 4 Step 1 tests — consistent.
- `logout_view` decorated with `@require_POST` in Task 3 Step 3, tested in Task 3 Step 1 — consistent.
- `url_has_allowed_host_and_scheme` imported in Task 2 Step 3, no naming conflicts.
