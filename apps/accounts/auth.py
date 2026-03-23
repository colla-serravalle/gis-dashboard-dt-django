"""
Custom OIDC authentication backend for Azure Active Directory (Entra ID).

Authentication flow:
- Azure AD handles identity verification via OIDC protocol
- Django retains full control over authorization (groups, permissions)
- On first login, a local Django user is auto-created from Azure claims
- On subsequent logins, user fields and group memberships are synced
- Superusers can still authenticate with local passwords (emergency fallback)
"""

import logging
from mozilla_django_oidc.auth import OIDCAuthenticationBackend
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import Group

from apps.audit.utils import emit_audit_event

logger = logging.getLogger(__name__)

# Map Azure group Object IDs to Django group names.
# Add entries here as new Azure groups need to be reflected in Django.
GROUP_MAPPING = {
    # 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx': 'django-group-name',
}


class AzureOIDCBackend(OIDCAuthenticationBackend):
    """OIDC backend that creates and syncs Django users from Azure AD claims."""

    def get_username(self, claims):
        """Derive a unique username from the email claim (prefix before '@')."""
        email = claims.get('email', '')
        return email.split('@')[0] if email else ''

    def filter_users_by_claims(self, claims):
        """Look up existing users by email address (case-insensitive)."""
        email = claims.get('email')
        if not email:
            return self.UserModel.objects.none()
        return self.UserModel.objects.filter(email__iexact=email)

    def create_user(self, claims):
        """Called on first Azure login — create a local Django user."""
        email = claims.get('email', '')
        username = self.get_username(claims)
        user = self.UserModel.objects.create_user(username=username, email=email)
        self.sync_user(user, claims)
        emit_audit_event(self.request, "auth.user.created", detail={"email": email})
        return user

    def update_user(self, user, claims):
        """Called on subsequent Azure logins — sync user fields and groups."""
        self.sync_user(user, claims)
        return user

    def sync_user(self, user, claims):
        """Sync first_name, last_name, email and Azure group memberships."""
        user.first_name = claims.get('given_name', '')
        user.last_name = claims.get('family_name', '')
        user.email = claims.get('email', user.email)
        user.save(update_fields=['first_name', 'last_name', 'email'])

        if not GROUP_MAPPING:
            logger.debug('Synced user %s: GROUP_MAPPING is empty, skipping group sync', user.email)
            return

        azure_group_ids = claims.get('groups', [])
        django_groups = []
        for azure_oid, django_group_name in GROUP_MAPPING.items():
            if azure_oid in azure_group_ids:
                group, _ = Group.objects.get_or_create(name=django_group_name)
                django_groups.append(group)

        # Only update groups that are covered by the mapping; leave others untouched.
        mapped_group_names = set(GROUP_MAPPING.values())
        managed_groups = Group.objects.filter(name__in=mapped_group_names)
        user.groups.remove(*managed_groups)
        if django_groups:
            user.groups.add(*django_groups)
        logger.debug(
            'Synced user %s: groups=%s',
            user.email,
            [g.name for g in django_groups],
        )


class SuperuserOnlyModelBackend(ModelBackend):
    """
    Restricts local password authentication to superusers only.

    Regular users must authenticate via Azure AD. Superusers retain
    local login access as an emergency fallback (e.g. for Django admin).
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        user = super().authenticate(request, username=username, password=password, **kwargs)
        if user and getattr(user, 'is_superuser', False):
            return user
        return None
