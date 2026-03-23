# Authorization Strategy: Service-Level Access via Django Groups

## Context

This project uses Azure AD (OIDC) for **authentication** via `mozilla-django-oidc` with a custom backend. **Authorization** is handled entirely within Django using Groups and permissions. Each Django app represents a "service", and access to each service is gated by Django Group membership.

Reference the technical spec at `docs/2026-03-06-claude_authorization_instructions.md` for authentication details.

## Architecture

```
Azure AD (authentication) → mozilla-django-oidc → Django User
                                                      ↓
                                               Django Groups
                                                      ↓
                                          Service Access Control
                                    (1 Group ↔ 1+ Django apps allowed)
```

**Principle**: Authentication tells us *who* the user is. Authorization (Groups → app access) tells us *what they can do*. These two concerns stay cleanly separated.

## Data Model

### Service Registry

Create a new app `authorization` (or add to an existing core app) with a `Service` model that maps Django apps to Groups:

```python
# authorization/models.py

from django.db import models
from django.contrib.auth.models import Group


class Service(models.Model):
    """
    Maps a Django app (identified by app_label) to the Groups
    that are allowed to access it.
    """
    name = models.CharField(max_length=100, help_text="Human-readable service name")
    app_label = models.CharField(
        max_length=100,
        unique=True,
        help_text="Django app label (e.g. 'reports', 'dashboard')"
    )
    allowed_groups = models.ManyToManyField(
        Group,
        related_name="accessible_services",
        blank=True,
        help_text="Groups that can access this service"
    )
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def user_has_access(self, user):
        """Check if a user can access this service."""
        if user.is_superuser:
            return True
        if not self.is_active:
            return False
        return self.allowed_groups.filter(
            id__in=user.groups.values_list("id", flat=True)
        ).exists()
```

### Admin Configuration

```python
# authorization/admin.py

from django.contrib import admin
from .models import Service


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "app_label", "is_active", "group_list")
    list_filter = ("is_active",)
    filter_horizontal = ("allowed_groups",)

    @admin.display(description="Allowed Groups")
    def group_list(self, obj):
        return ", ".join(g.name for g in obj.allowed_groups.all())
```

## Middleware

Create middleware that checks service access on every request based on URL → app_label resolution:

```python
# authorization/middleware.py

from django.http import HttpResponseForbidden
from django.urls import resolve, Resolver404
from django.conf import settings

from .models import Service


# Apps that are always accessible (no group check)
EXEMPT_APP_LABELS = getattr(settings, "SERVICE_AUTH_EXEMPT_APPS", [
    "authorization",  # the auth app itself
    "admin",          # Django admin (has its own permission system)
    "oidc",           # mozilla-django-oidc callback URLs
])

# URL prefixes that skip authorization entirely (login, static, etc.)
EXEMPT_URL_PREFIXES = getattr(settings, "SERVICE_AUTH_EXEMPT_URLS", [
    "/oidc/",
    "/admin/",
    "/static/",
    "/health/",
])


class ServiceAccessMiddleware:
    """
    Enforces service-level access control.
    Resolves the current request URL to a Django app_label,
    then checks if the user belongs to a Group that has
    access to that service.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip for unauthenticated users (let auth middleware handle redirect)
        if not hasattr(request, "user") or not request.user.is_authenticated:
            return self.get_response(request)

        # Skip exempt URL prefixes
        if any(request.path.startswith(prefix) for prefix in EXEMPT_URL_PREFIXES):
            return self.get_response(request)

        # Superusers bypass all service checks
        if request.user.is_superuser:
            return self.get_response(request)

        # Resolve URL to app_label
        try:
            match = resolve(request.path)
            app_label = match.app_name or match.func.__module__.split(".")[0]
        except (Resolver404, AttributeError, IndexError):
            return self.get_response(request)

        # Skip exempt apps
        if app_label in EXEMPT_APP_LABELS:
            return self.get_response(request)

        # Check service access
        try:
            service = Service.objects.get(app_label=app_label, is_active=True)
        except Service.DoesNotExist:
            # If no Service record exists, the app is unprotected (or deny by default)
            # Choose your policy here:
            #   return self.get_response(request)          # allow if unregistered
            #   return HttpResponseForbidden("...")         # deny if unregistered
            return HttpResponseForbidden("...")

        if not service.user_has_access(request.user):
            return HttpResponseForbidden(
                "You do not have permission to access this service. "
                "Contact your administrator to request access."
            )

        return self.get_response(request)
```

### Register Middleware

In `settings.py`, add the middleware **after** authentication and session middleware:

```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "mozilla_django_oidc.middleware.SessionRefresh",
    # ↓ Service access check runs after user is authenticated
    "authorization.middleware.ServiceAccessMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
```

## Decorator for View-Level Checks (Optional)

For finer-grained control within an app, provide a decorator:

```python
# authorization/decorators.py

from functools import wraps
from django.http import HttpResponseForbidden
from .models import Service


def require_service(app_label):
    """
    View decorator that checks access to a specific service.
    Use when a view in one app needs to gate on another app's service.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            try:
                service = Service.objects.get(app_label=app_label, is_active=True)
            except Service.DoesNotExist:
                return view_func(request, *args, **kwargs)
            if not service.user_has_access(request.user):
                return HttpResponseForbidden(
                    "You do not have permission to access this service."
                )
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
```

Usage:
```python
from authorization.decorators import require_service

@require_service("reports")
def export_report(request):
    ...
```

## Template Context Processor

Expose accessible services to templates (for navigation menus):

```python
# authorization/context_processors.py

from .models import Service


def accessible_services(request):
    """Add the list of services the current user can access to template context."""
    if not hasattr(request, "user") or not request.user.is_authenticated:
        return {"accessible_services": []}

    if request.user.is_superuser:
        services = Service.objects.filter(is_active=True)
    else:
        services = Service.objects.filter(
            is_active=True,
            allowed_groups__in=request.user.groups.all()
        ).distinct()

    return {"accessible_services": services}
```

Register in `settings.py`:
```python
TEMPLATES = [{
    "OPTIONS": {
        "context_processors": [
            # ... existing processors ...
            "authorization.context_processors.accessible_services",
        ],
    },
}]
```

## Azure AD Group → Django Group Sync

In your existing custom OIDC backend, ensure Azure group claims are mapped to Django Groups. The authorization layer then works automatically since it checks Django Group membership:

```python
# In your custom OIDCAuthenticationBackend.create_user / update_user:
# 1. Read group claims from the ID token
# 2. Map Azure group IDs/names → Django Group objects
# 3. Set user.groups accordingly
#
# The Service model's allowed_groups references these same Django Groups,
# so group sync is the only bridge between Azure AD and service access.
```

## Management Command: Seed Services

```python
# authorization/management/commands/seed_services.py

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from authorization.models import Service


# Define your app→groups mapping here
SERVICE_DEFINITIONS = [
    {
        "name": "Reports",
        "app_label": "reports",
        "description": "Reporting and analytics",
        "groups": ["reports_users", "managers"],
    },
    {
        "name": "Dashboard",
        "app_label": "dashboard",
        "description": "Main dashboard",
        "groups": ["dashboard_users", "managers"],
    },
    # Add more services as needed
]


class Command(BaseCommand):
    help = "Create or update Service records and their group associations"

    def handle(self, *args, **options):
        for svc_def in SERVICE_DEFINITIONS:
            service, created = Service.objects.update_or_create(
                app_label=svc_def["app_label"],
                defaults={
                    "name": svc_def["name"],
                    "description": svc_def.get("description", ""),
                    "is_active": True,
                },
            )
            groups = []
            for group_name in svc_def.get("groups", []):
                group, _ = Group.objects.get_or_create(name=group_name)
                groups.append(group)
            service.allowed_groups.set(groups)

            status = "Created" if created else "Updated"
            self.stdout.write(f"{status}: {service.name} ({service.app_label})")
```

## Settings

```python
# settings.py — Service authorization config

# Apps that bypass service access checks
SERVICE_AUTH_EXEMPT_APPS = [
    "authorization",
    "admin",
    "oidc",
]

# URL prefixes that bypass service access checks
SERVICE_AUTH_EXEMPT_URLS = [
    "/oidc/",
    "/admin/",
    "/static/",
    "/health/",
]

# Policy for apps without a Service record: "allow" or "deny"
SERVICE_AUTH_DEFAULT_POLICY = "deny"
```

## Testing

Write tests covering these scenarios:

1. **Unauthenticated user** → middleware passes through (let OIDC handle redirect)
2. **Superuser** → always allowed, regardless of group membership
3. **User in correct group** → access granted
4. **User NOT in correct group** → 403 Forbidden
5. **Inactive service** → access denied (or allowed, depending on policy)
6. **Unregistered app** → follows `SERVICE_AUTH_DEFAULT_POLICY`
7. **Exempt URLs** → always pass through
8. **Azure group sync** → after login, user.groups reflects Azure membership and service access updates accordingly

## Implementation Order

1. Create the `authorization` app and `Service` model, run migrations
2. Register `ServiceAdmin` in admin
3. Add `ServiceAccessMiddleware` to settings
4. Add the context processor for template navigation
5. Create the `seed_services` management command with your actual app→group mapping
6. Write tests
7. (Optional) Add the `@require_service` decorator where needed
