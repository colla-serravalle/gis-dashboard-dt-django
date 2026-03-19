from .models import Service


def accessible_services(request):
    """Add the list of services the current user can access to template context.

    Provides two context variables:
    - ``accessible_services``: all active services the user can access.
    - ``displayable_services``: subset that have a ``list_url_name`` configured
      and can therefore be rendered as home-page cards.
    """
    if not hasattr(request, "user") or not request.user.is_authenticated:
        return {"accessible_services": [], "displayable_services": []}

    if request.user.is_superuser:
        services = Service.objects.filter(is_active=True)
    else:
        services = Service.objects.filter(
            is_active=True,
            allowed_groups__in=request.user.groups.all()
        ).distinct()

    displayable = services.exclude(list_url_name="").exclude(list_url_name__isnull=True)

    return {"accessible_services": services, "displayable_services": displayable}
