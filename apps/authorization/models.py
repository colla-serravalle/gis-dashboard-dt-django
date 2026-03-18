from django.db import models
from django.contrib.auth.models import Group
from django.urls import reverse, NoReverseMatch


class Service(models.Model):
    """
    Maps a URL namespace (app_label) to the Groups that are allowed to access it.
    """
    name = models.CharField(max_length=100, help_text="Human-readable service name")
    app_label = models.CharField(
        max_length=100,
        unique=True,
        help_text="URL namespace of the Django app (e.g. 'reports', 'core')"
    )
    allowed_groups = models.ManyToManyField(
        Group,
        related_name="accessible_services",
        blank=True,
        help_text="Groups that can access this service"
    )
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    icon_class = models.CharField(
        max_length=100,
        blank=True,
        help_text="Font Awesome class string, e.g. 'fa-solid fa-file-invoice'"
    )
    list_url_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Django URL name for this service's list page, e.g. 'reports:report_list'"
    )
    display_order = models.IntegerField(
        default=0,
        help_text="Controls display order in home page and sidebar (lower = first)"
    )

    class Meta:
        ordering = ["display_order", "name"]

    def __str__(self):
        return self.name

    @property
    def get_list_url(self):
        """Return the resolved URL for this service's list page, or empty string."""
        if not self.list_url_name:
            return ""
        try:
            return reverse(self.list_url_name)
        except NoReverseMatch:
            return ""

    def user_has_access(self, user):
        """Check if a user can access this service."""
        if user.is_superuser:
            return True
        if not self.is_active:
            return False
        return self.allowed_groups.filter(
            id__in=user.groups.values_list("id", flat=True)
        ).exists()
