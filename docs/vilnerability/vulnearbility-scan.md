Vunerability scan report for GIS Dashboard Django
  ---
  CRITICAL

  C-1. Real ArcGIS Credentials in .env File
  - ARCGIS_USERNAME and ARCGIS_PASSWORD are plaintext in the .env file.
  - Action: Rotate the ArcGIS password immediately. Confirm via git log --all -p -- .env it was never committed. Consider Azure Key Vault for production.

  C-2. Insecure Default SECRET_KEY — config/settings.py:40
  - Falls back to 'django-insecure-change-this-in-production' if the env var is missing.
  - Action: Replace with SECRET_KEY = os.environ['SECRET_KEY'] — fail loudly if missing.

  ---
  HIGH

  H-1. Open Redirect in Login View — apps/accounts/views.py:90-91
  - next_url = request.GET.get('next', '/') passed directly to redirect() with no validation. Enables phishing via /auth/login/?next=https://evil.com.
  - Action: Use url_has_allowed_host_and_scheme() before redirecting.

  H-2. All Production Security Headers Missing — config/settings.py
  - SECURE_SSL_REDIRECT, SECURE_HSTS_SECONDS, SESSION_COOKIE_SECURE, CSRF_COOKIE_SECURE, SECURE_CONTENT_TYPE_NOSNIFF — none are configured.
  - Action: Add a production-only block with all these settings set.

  H-3. DEBUG Defaults to True — config/settings.py:43
  - os.getenv('DEBUG', 'True') — if env var is missing in production, full stack traces are exposed.
  - Action: Change default to 'False'.

  H-4. ArcGIS WHERE Clause Injection — apps/reports/services/report_data.py:26,37-39
  - report_id from request.GET is inserted directly into f-string WHERE clauses with no format validation.
  - Action: Validate report_id matches a GUID pattern via regex before use.

  H-5. Exception Details Leaked to Clients — apps/reports/views/api.py:250,328,357
  - return JsonResponse({'error': str(e)}, status=500) exposes raw exception messages.
  - Action: Return generic messages; the full exception is already logged server-side.

  H-6. Logout via GET Without CSRF — apps/accounts/views.py:120-125
  - Any page can force-logout a user with an <img> tag pointing to /auth/logout/.
  - Action: Add @require_POST and use a CSRF-protected form in the template.

  ---
  MEDIUM

  ┌─────┬──────────────────────────────────────────────────────────────────────────────┬─────────────────────────────────────┐
  │  #  │                                   Finding                                    │              Location               │
  ├─────┼──────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────────┤
  │ M-1 │ Session-based rate limiting trivially bypassable (reset by clearing cookies) │ accounts/views.py:54-74             │
  ├─────┼──────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────────┤
  │ M-2 │ No MAX_ITEMS_PER_PAGE enforcement — per_page can be set to any value         │ reports/views/api.py:178            │
  ├─────┼──────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────────┤
  │ M-3 │ CDN assets lack Subresource Integrity (SRI) hashes                           │ templates/base.html:11              │
  ├─────┼──────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────────┤
  │ M-4 │ SQLite in production — no concurrent write support, file accessible          │ config/settings.py:106-111          │
  ├─────┼──────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────────┤
  │ M-5 │ Naive (timezone-unaware) timestamps despite USE_TZ = True                    │ reports/mappings.py:455, api.py:115 │
  ├─────┼──────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────────┤
  │ M-6 │ Django admin at default /admin/ path, excluded from ServiceAccessMiddleware  │ config/urls.py:12                   │
  └─────┴──────────────────────────────────────────────────────────────────────────────┴─────────────────────────────────────┘

  ---
  LOW / Informational

  ┌─────┬──────────────────────────────────────────────────────────────────────────────┐
  │  #  │                                   Finding                                    │
  ├─────┼──────────────────────────────────────────────────────────────────────────────┤
  │ L-1 │ No Content-Security-Policy header configured                                 │
  ├─────┼──────────────────────────────────────────────────────────────────────────────┤
  │ L-2 │ |safe filter used unnecessarily on integer values in templates               │
  ├─────┼──────────────────────────────────────────────────────────────────────────────┤
  │ L-3 │ service.icon_class rendered in class attribute (auto-escaped, informational) │
  ├─────┼──────────────────────────────────────────────────────────────────────────────┤
  │ L-4 │ Corporate logo loaded from external URL — host it locally                    │
  ├─────┼──────────────────────────────────────────────────────────────────────────────┤
  │ L-5 │ ArcGIS singleton not thread-safe (benign in practice)                        │
  └─────┴──────────────────────────────────────────────────────────────────────────────┘

  ---
  Positive Findings

  The following are already well-implemented:
  - CSRF protection globally enabled and used in forms
  - All views require @login_required
  - Django template auto-escaping active everywhere
  - format_html used instead of mark_safe in template tags
  - SuperuserOnlyModelBackend restricts password auth to superusers
  - NIS2 audit logging is comprehensive
  - escapeHtml() used correctly in JS for dynamic DOM insertion
  - ArcGIS token caching uses proper double-checked locking

  ---
  Priority Remediation Order

  1. Rotate ArcGIS credentials — now
  2. Fix SECRET_KEY default — now
  3. Default DEBUG=False + add security headers — before production
  4. Fix open redirect (H-1) — before production
  5. Validate report_id (H-4) — before production
  6. Sanitize error responses (H-5) — before production
  7. Fix logout CSRF (H-6) — before production
  8. Fix rate limiting (M-1) — before production
  9. Everything else — next sprint