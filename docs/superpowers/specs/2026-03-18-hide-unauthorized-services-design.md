# Design: Hide Unauthorized Services in Home Page and Sidebar

**Date:** 2026-03-18
**Branch:** feature/hide-unauthorized-apps
**Status:** Approved

---

## Overview

Users currently see all service cards on the home page and all service links in the sidebar regardless of their RBAC group membership. This change makes the UI reflect access control: only services the user can actually access are shown.

The existing `ServiceAccessMiddleware` already blocks unauthorized requests with a 403. This feature closes the UX gap by removing dead links before the user ever clicks them.

---

## Context

### Existing Infrastructure (no changes needed)

- `apps/authorization/models.py` — `Service` model with `app_label`, `allowed_groups`, `is_active`, and `user_has_access(user)` method
- `apps/authorization/middleware.py` — `ServiceAccessMiddleware` enforces access at the request level
- `apps/authorization/context_processors.py` — `accessible_services` context processor injects a QuerySet of accessible `Service` objects into every template; already registered in `settings.py`

### Problem

- `templates/core/home.html` hardcodes both service cards with no access check
- `templates/includes/sidebar.html` hardcodes both service links in the "Servizi" submenu with no access check
- The `Service` model has no UI metadata (icon, link URL), making dynamic rendering impossible today

---

## Design

### 1. Model Changes — `apps/authorization/models.py`

Add three fields to the `Service` model:

| Field | Type | Default | Purpose |
|---|---|---|---|
| `icon_class` | `CharField(max_length=100, blank=True)` | `""` | Full Font Awesome class string, e.g. `"fa-solid fa-file-invoice"` |
| `list_url_name` | `CharField(max_length=200, blank=True)` | `""` | Django URL name for the service list page, e.g. `"reports:report_list"` |
| `display_order` | `IntegerField(default=0)` | `0` | Controls card/link ordering |

Update `Meta.ordering` from `["name"]` to `["display_order", "name"]`. This ordering applies globally to all `Service.objects` queries including the `accessible_services` context processor, which is safe on SQLite3. (Note: if the database is ever migrated to PostgreSQL, the `ORDER BY` + `DISTINCT` combination on the many-to-many join in the context processor would need review.)

Both string fields are `blank=True` so existing `Service` rows remain valid during transition. A service with an empty `list_url_name` will not render a working link, but this is only a transitional state resolved by re-running the seed command.

Add a `get_list_url()` property to `Service` that resolves the stored URL name safely:

```python
from django.urls import reverse, NoReverseMatch

@property
def get_list_url(self):
    """Return the resolved URL for this service's list page, or empty string."""
    if not self.list_url_name:
        return ""
    try:
        return reverse(self.list_url_name)
    except NoReverseMatch:
        return ""
```

The `@property` decorator is required so that both Python code (`service.get_list_url`) and Django templates (`{{ service.get_list_url }}`) access it without parentheses. Django's template engine calls zero-argument callables automatically, so `@property` is not strictly required for templates to work, but it is the correct Python convention and keeps the interface consistent.

Templates call `{{ service.get_list_url }}` rather than using `{% url %}` with a variable, which avoids relying on Django template tag variable resolution behaviour and handles misconfigured URL names gracefully.

### 2. Migration

One auto-generated migration adds the three new fields to `authorization_service`. No destructive changes.

### 3. Seed Command — `apps/authorization/management/commands/seed_services.py`

Add `icon_class`, `list_url_name`, and `display_order` to the two UI-visible service definitions:

```python
{
    "name": "Reports",
    "app_label": "reports",
    "description": "Field inspection reports and PDF export",
    "groups": ["reports_users", "managers"],
    "icon_class": "fa-solid fa-file-invoice",
    "list_url_name": "reports:report_list",
    "display_order": 1,
},
{
    "name": "Segnalazioni",
    "app_label": "segnalazioni",
    "description": "Archivio delle segnalazioni ricevute.",
    "groups": ["segnalazioni_users", "managers"],
    "icon_class": "fa-solid fa-triangle-exclamation",
    "list_url_name": "segnalazioni:segnalazioni_list",
    "display_order": 2,
},
```

The command uses `update_or_create`, so re-running it on an existing database populates the new fields without duplicating records.

The other four service entries (`core`, `reports_api`, `segnalazioni_api`, `profiles`) are **not given** `icon_class`, `list_url_name`, or `display_order` keys. Their rows keep the field defaults (`""`, `""`, `0`) set by the migration. They are skipped in the UI by the `{% if service.get_list_url %}` guard in both templates, and their RBAC behaviour is unchanged.

### 4. Home Page Template — `templates/core/home.html`

Replace the hardcoded grid columns with a data-driven loop:

```django
{% if accessible_services %}
<div class="text-chunk">
    <h1>Servizi</h1>
    <p>Elenco dei principali servizi disponibili.</p>
</div>
<div class="grid-container columns-3">
    {% for service in accessible_services %}
    {% if service.get_list_url %}
    <div class="grid-column">
        <div class="icon-background">
            <i class="{{ service.icon_class }} fa-3x"></i>
        </div>
        <h2>{{ service.name }}</h2>
        <p>{{ service.description }}</p>
        <a href="{{ service.get_list_url }}" class="standard-link filled-link">Vai alla pagina</a>
    </div>
    {% endif %}
    {% endfor %}
</div>
{% endif %}
```

- The outer `{% if accessible_services %}` hides the entire section (heading + grid) when the user has no accessible services
- The inner `{% if service.get_list_url %}` skips API/backend services that have no UI page

### 5. Sidebar Template — `templates/includes/sidebar.html`

Wrap the "Servizi" `<li>` in `{% if accessible_services %}` and replace the hardcoded submenu links with a loop:

```django
{% if accessible_services %}
<li>
    <button onClick="toggleSubMenu(this)" class="dropdown-link">
        ...icon and chevron SVGs unchanged...
        <span>Servizi</span>
        ...
    </button>
    <ul class="sub-menu">
        <div>
            {% for service in accessible_services %}
            {% if service.get_list_url %}
            <li><a href="{{ service.get_list_url }}">{{ service.name }}</a></li>
            {% endif %}
            {% endfor %}
        </div>
    </ul>
</li>
{% endif %}
```

- If the user has no accessible services, the entire "Servizi" menu item is hidden
- The inner `{% if service.get_list_url %}` guard prevents rendering broken links for API-only services

---

## Data Flow

```
Request → ServiceAccessMiddleware (blocks 403 if unauthorized)
       → context_processors.accessible_services (injects QuerySet into template context)
       → home.html / sidebar.html (renders only accessible service cards/links)
```

---

## What Is Not Changed

- `ServiceAccessMiddleware` — no changes; continues to enforce access at request level
- `Service.user_has_access()` — no changes
- `accessible_services` context processor — no changes
- RBAC group/service configuration — no changes to existing groups or permissions
- Non-UI services (`core`, `reports_api`, `segnalazioni_api`, `profiles`) — no UI entries added; RBAC unchanged

---

## Adding a New Service in the Future

1. Add an entry to `SERVICE_DEFINITIONS` in `seed_services.py` with `icon_class`, `list_url_name`, and `display_order`
2. Run `python manage.py seed_services`
3. The service appears automatically on the home page and sidebar for users in the configured groups — no template changes required

---

## Testing Considerations

- A user in `reports_users` only sees the Reports card/link
- A user in `segnalazioni_users` only sees the Segnalazioni card/link
- A user in `managers` sees both
- A user in no relevant groups sees neither (section and submenu hidden)
- A superuser sees all active services with a non-empty `get_list_url`
- A `Service` with a blank or invalid `list_url_name` is skipped in the UI (`get_list_url` returns `""` and the `{% if %}` guard hides it); no exception is raised
