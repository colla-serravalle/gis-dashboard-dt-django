from django.http import HttpResponseForbidden
from django.urls import resolve, Resolver404
from django.conf import settings

from .models import Service
from apps.audit.utils import emit_audit_event


# Apps (URL namespaces) that are always accessible — no group check needed
EXEMPT_APP_LABELS = getattr(settings, "SERVICE_AUTH_EXEMPT_APPS", [
    "authorization",
    "admin",
    "oidc",
    "accounts",
])

# URL prefixes that skip authorization entirely
EXEMPT_URL_PREFIXES = getattr(settings, "SERVICE_AUTH_EXEMPT_URLS", [
    "/oidc/",
    "/admin/",
    "/static/",
    "/health/",
    "/auth/",
    "/accounts/",
])

# Policy when no Service record exists for an app: "allow" or "deny"
DEFAULT_POLICY = getattr(settings, "SERVICE_AUTH_DEFAULT_POLICY", "deny")


class ServiceAccessMiddleware:
    """
    Enforces service-level access control.

    Resolves the current request URL to a Django URL namespace (app_name),
    then checks if the user belongs to a Group that has access to that service.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip for unauthenticated users — let auth middleware handle redirect
        if not hasattr(request, "user") or not request.user.is_authenticated:
            return self.get_response(request)

        # Skip exempt URL prefixes
        if any(request.path.startswith(prefix) for prefix in EXEMPT_URL_PREFIXES):
            return self.get_response(request)

        # Superusers bypass all service checks
        if request.user.is_superuser:
            return self.get_response(request)

        # Resolve URL to app namespace
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
            if DEFAULT_POLICY == "allow":
                return self.get_response(request)
            emit_audit_event(request, "authz.access.denied", detail={
                "app_label": app_label,
                "reason": "service_not_found",
            })
            return HttpResponseForbidden(
                "You do not have permission to access this service. "
                "Contact your administrator to request access."
            )

        if not service.user_has_access(request.user):
            emit_audit_event(request, "authz.access.denied", detail={
                "app_label": app_label,
                "reason": "group_not_permitted",
            })
            return HttpResponseForbidden(
                "You do not have permission to access this service. "
                "Contact your administrator to request access."
            )

        return self.get_response(request)
