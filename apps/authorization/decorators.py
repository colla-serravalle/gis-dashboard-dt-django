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
