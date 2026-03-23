# Azure AD Authentication Integration

## Goal

Integrate Azure Active Directory (Entra ID) as the authentication provider for this Django application using the OIDC protocol via `mozilla-django-oidc`. Azure AD handles **authentication** (identity verification), while Django's built-in auth system retains full control over **authorization** (groups, permissions, object-level access). On first login, a local Django user is automatically created and synced. Regular users must authenticate via Azure; superusers retain local login access as an emergency fallback.

---

## Dependencies

Install with uv:

```bash
uv add mozilla-django-oidc
```

This will automatically update `pyproject.toml` and `uv.lock`.

---

## Environment Variables

Add to `.env` (never hardcode secrets):

```env
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
```

Load them in `settings.py` using `os.environ.get()` or `python-decouple` / `django-environ` if already in use.

---

## Azure Portal Configuration (manual step — not automated)

Before running the integration, the following must be configured manually in **Azure Portal → Entra ID → App Registrations**:

1. Create a new App Registration (or use existing)
2. Set Redirect URI to: `https://<your-domain>/oidc/callback/`
3. Under **Certificates & secrets**, create a Client Secret
4. Under **Token configuration → Add groups claim**, enable **Security groups** for ID token and Access token
5. Note down: Tenant ID, Client ID, Client Secret

---

## Files to Create

### `your_app/auth.py`

Custom OIDC authentication backend. Must implement:

- `create_user(claims)` — called on first login, creates local Django user
- `update_user(user, claims)` — called on subsequent logins, syncs user fields
- `sync_user(user, claims)` — shared logic: sync `first_name`, `last_name`, `email`; map Azure group OIDs to Django groups via `GROUP_MAPPING`
- `get_username(claims)` — derive username from email (prefix before `@`)
- `filter_users_by_claims(claims)` — look up existing users by email (case-insensitive)

**Group sync logic:**

```python
GROUP_MAPPING = {
    'xxxxxxxx-azure-group-object-id': 'django-group-name',
    # add mappings as needed
}
```

Azure groups are passed as a list of UUIDs in `claims.get('groups', [])`. Map them to Django `Group` objects and call `user.groups.set(...)`.

> **Note:** If a user belongs to more than 200 Azure groups, the token will contain an overage indicator instead of group IDs. In that case, override `get_userinfo()` to query MS Graph API at `https://graph.microsoft.com/v1.0/me/memberOf`.

---

### `your_app/backends.py` *(or add to `auth.py`)*

Custom `ModelBackend` subclass that restricts local password login to superusers only:

```python
class SuperuserOnlyModelBackend(ModelBackend):
    def authenticate(self, request, **kwargs):
        user = super().authenticate(request, **kwargs)
        if user and user.is_superuser:
            return user
        return None
```

---

## Files to Modify

### `settings.py`

Add/modify the following sections:

```python
INSTALLED_APPS = [
    ...
    'mozilla_django_oidc',
]

MIDDLEWARE = [
    ...
    # Add after SessionMiddleware and AuthenticationMiddleware:
    'mozilla_django_oidc.middleware.SessionRefresh',
]

AUTHENTICATION_BACKENDS = [
    'your_app.auth.AzureOIDCBackend',
    'your_app.auth.SuperuserOnlyModelBackend',
]

# Azure OIDC settings
TENANT_ID = os.environ.get('AZURE_TENANT_ID')
OIDC_RP_CLIENT_ID = os.environ.get('AZURE_CLIENT_ID')
OIDC_RP_CLIENT_SECRET = os.environ.get('AZURE_CLIENT_SECRET')

OIDC_RP_SIGN_ALGO = 'RS256'
OIDC_OP_JWKS_ENDPOINT = f'https://login.microsoftonline.com/{TENANT_ID}/discovery/v2.0/keys'
OIDC_OP_AUTHORIZATION_ENDPOINT = f'https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/authorize'
OIDC_OP_TOKEN_ENDPOINT = f'https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token'
OIDC_OP_USER_ENDPOINT = 'https://graph.microsoft.com/oidc/userinfo'

OIDC_RP_SCOPES = 'openid email profile'

LOGIN_URL = '/oidc/authenticate/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# Renew OIDC token every 15 minutes (SessionRefresh middleware)
OIDC_RENEW_ID_TOKEN_EXPIRY_SECONDS = 900
```

---

### `urls.py` (project-level)

```python
from django.urls import path, include

urlpatterns = [
    ...
    path('oidc/', include('mozilla_django_oidc.urls')),
    # Redirect legacy login URL to OIDC
    path('accounts/login/', RedirectView.as_view(url='/oidc/authenticate/', permanent=False)),
]
```

---

## Behavior Specification

| Scenario | Expected behavior |
|---|---|
| User logs in for the first time via Azure | Local Django user is created; `first_name`, `last_name`, `email` populated from claims; groups synced from Azure group claims |
| User logs in again | User fields and group memberships updated from latest claims |
| User is removed from an Azure group | On next login, the corresponding Django group membership is removed |
| Superuser uses local admin login | Allowed via `SuperuserOnlyModelBackend` |
| Regular user attempts local password login | Authentication fails — redirected to Azure |
| Session expires | `SessionRefresh` middleware silently renews token; user is redirected to Azure if renewal fails |
| User is not in Azure AD | Authentication rejected; user not created |

---

## Do NOT Modify

- Existing permission logic in any `permissions.py` files
- Existing `Group` definitions and permission assignments
- Any model-level `has_perm` or `has_object_perm` overrides
- Django admin registration files (`admin.py`)
- Existing user model if a custom `AbstractUser` is already in use — only extend it if needed

---

## Django Admin Considerations

The default Django admin login form uses local authentication. To keep it functional for superusers without changes, `SuperuserOnlyModelBackend` handles this automatically. No changes to `admin.py` are required unless full SSO for the admin panel is explicitly requested.

---

## Testing & Verification

After implementation, verify:

1. Visiting any `@login_required` view redirects to `/oidc/authenticate/` (Azure login page)
2. After Azure login, user is redirected back and a local `User` object exists in the database with correct `email`, `first_name`, `last_name`
3. Django groups are correctly assigned based on `GROUP_MAPPING`
4. Superuser can still log in at `/admin/` using local credentials
5. Regular users cannot log in at `/admin/` with a local password
6. Logging out clears the Django session

For local development, you can use a test Azure tenant or mock OIDC provider (e.g. `dex`, `keycloak`) — set `OIDC_*` endpoints accordingly in `.env`.

---

## References

- [mozilla-django-oidc docs](https://mozilla-django-oidc.readthedocs.io/)
- [Azure AD OIDC endpoints](https://learn.microsoft.com/en-us/azure/active-directory/develop/v2-protocols-oidc)
- [MS Graph group membership (overage)](https://learn.microsoft.com/en-us/azure/active-directory/develop/id-token-claims-reference#groups-overage-claim)
