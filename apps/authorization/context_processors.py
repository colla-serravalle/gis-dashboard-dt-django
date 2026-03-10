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
