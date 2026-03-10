from django.db import models
from django.contrib.auth.models import Group


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
