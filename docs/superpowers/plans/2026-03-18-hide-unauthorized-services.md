# Hide Unauthorized Services Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the home page and sidebar only show service cards/links the authenticated user actually has access to, driven by the existing RBAC data in SQLite3.

**Architecture:** Add three UI metadata fields (`icon_class`, `list_url_name`, `display_order`) and a `get_list_url` property to the existing `Service` model. The already-registered `accessible_services` context processor injects the right QuerySet into every template — only the templates need updating to iterate it instead of hardcoding both services.

**Tech Stack:** Django 6, SQLite3, Django ORM, Django TestCase (test runner: `python manage.py test`), Django template language, Font Awesome icons.

---

## File Map

| File | Action | What changes |
|---|---|---|
| `apps/authorization/models.py` | Modify | Add `icon_class`, `list_url_name`, `display_order` fields; add `get_list_url` property; update `Meta.ordering` |
| `apps/authorization/tests.py` | **Create** | Unit tests for `get_list_url` and template integration tests |
| `apps/authorization/migrations/0002_service_ui_fields.py` | **Create** | Auto-generated migration adding the three new fields |
| `apps/authorization/management/commands/seed_services.py` | Modify | Add `icon_class`, `list_url_name`, `display_order` to Reports and Segnalazioni entries |
| `templates/core/home.html` | Modify | Replace hardcoded cards with `{% for service in accessible_services %}` loop |
| `templates/includes/sidebar.html` | Modify | Wrap "Servizi" `<li>` in `{% if accessible_services %}` and replace hardcoded links with loop |

---

## Task 1: Add UI Fields and `get_list_url` Property to Service Model (TDD)

**Files:**
- Modify: `apps/authorization/models.py`
- Create: `apps/authorization/tests.py`

### Reference

The current `Service` model (`apps/authorization/models.py`) has: `name`, `app_label`, `allowed_groups`, `is_active`, `description`, `user_has_access(user)`. `Meta.ordering = ["name"]`.

The `accessible_services` context processor (`apps/authorization/context_processors.py`) returns a queryset filtered by the user's groups, already registered in `settings.py`. No changes needed there.

---

- [ ] **Step 1.1: Write failing tests**

Create `apps/authorization/tests.py` with this content:

```python
from django.contrib.auth.models import User, Group
from django.test import TestCase, Client
from django.urls import reverse

from apps.authorization.models import Service


class ServiceGetListUrlTest(TestCase):
    """Unit tests for Service.get_list_url property."""

    def test_returns_resolved_url_for_valid_url_name(self):
        service = Service(list_url_name="reports:report_list")
        url = service.get_list_url
        self.assertEqual(url, reverse("reports:report_list"))

    def test_returns_empty_string_for_blank_url_name(self):
        service = Service(list_url_name="")
        self.assertEqual(service.get_list_url, "")

    def test_returns_empty_string_for_invalid_url_name(self):
        service = Service(list_url_name="nonexistent:view")
        self.assertEqual(service.get_list_url, "")


class ServiceOrderingTest(TestCase):
    """Service queryset is ordered by display_order then name."""

    def test_ordering_by_display_order_then_name(self):
        Service.objects.create(name="Z Service", app_label="z_svc", display_order=2)
        Service.objects.create(name="A Service", app_label="a_svc", display_order=1)
        Service.objects.create(name="M Service", app_label="m_svc", display_order=1)
        names = list(Service.objects.values_list("name", flat=True))
        self.assertEqual(names, ["A Service", "M Service", "Z Service"])


class HomePageServiceVisibilityTest(TestCase):
    """Integration tests: home page only shows accessible services."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user("testuser", password="pass")

        # Groups
        self.dashboard_group = Group.objects.create(name="dashboard_users_test")
        self.reports_group = Group.objects.create(name="reports_users_test")
        self.user.groups.add(self.dashboard_group, self.reports_group)

        # core Service — required so ServiceAccessMiddleware allows home page access
        core_svc = Service.objects.create(
            name="Dashboard", app_label="core", is_active=True, display_order=0
        )
        core_svc.allowed_groups.set([self.dashboard_group])

        # Reports service — user has access
        reports_svc = Service.objects.create(
            name="Reports",
            app_label="reports",
            is_active=True,
            icon_class="fa-solid fa-file-invoice",
            list_url_name="reports:report_list",
            display_order=1,
        )
        reports_svc.allowed_groups.set([self.reports_group])

        # Segnalazioni service — user does NOT have access (no groups set)
        Service.objects.create(
            name="Segnalazioni",
            app_label="segnalazioni",
            is_active=True,
            icon_class="fa-solid fa-triangle-exclamation",
            list_url_name="segnalazioni:segnalazioni_list",
            display_order=2,
        )

        self.client.force_login(self.user)

    def test_user_sees_only_accessible_service_card(self):
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Reports")
        self.assertNotContains(response, "Segnalazioni")

    def test_superuser_sees_all_services(self):
        superuser = User.objects.create_superuser("admin_test", password="pass")
        self.client.force_login(superuser)
        response = self.client.get(reverse("core:home"))
        self.assertContains(response, "Reports")
        self.assertContains(response, "Segnalazioni")

    def test_user_with_no_services_sees_no_services_section(self):
        # Create a user with only dashboard access (no service cards)
        bare_user = User.objects.create_user("bare_user", password="pass")
        bare_user.groups.add(self.dashboard_group)
        self.client.force_login(bare_user)
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "grid-container columns-3")
```

- [ ] **Step 1.2: Run tests — confirm they all fail**

```bash
python manage.py test apps.authorization.tests -v 2
```

Expected: multiple failures — `Service` has no `display_order` field, `get_list_url` does not exist.

- [ ] **Step 1.3: Add fields and property to the Service model**

Open `apps/authorization/models.py`. The file currently starts with `from django.db import models` and `from django.contrib.auth.models import Group`. Make these changes:

**Add import** at the top (alongside existing imports):
```python
from django.urls import reverse, NoReverseMatch
```

**Add three fields** inside the `Service` class, after the `description` field:
```python
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
```

**Update `Meta.ordering`**:
```python
class Meta:
    ordering = ["display_order", "name"]
```

**Add property** after the `__str__` method:
```python
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

- [ ] **Step 1.4: Run tests — confirm they still fail (migration not yet applied)**

```bash
python manage.py test apps.authorization.tests -v 2
```

Expected: `OperationalError: table authorization_service has no column named display_order` — this is correct, migration comes next.

- [ ] **Step 1.5: Do not commit yet**

The model and tests cannot be committed without their migration — any developer who checks out a commit where the model has new fields but no migration will hit `OperationalError: table authorization_service has no column named display_order`. The commit happens in Task 2 once the migration exists.

---

## Task 2: Generate and Apply Migration

**Files:**
- Create: `apps/authorization/migrations/0002_service_ui_fields.py` (auto-generated)

---

- [ ] **Step 2.1: Generate migration**

```bash
python manage.py makemigrations authorization --name service_ui_fields
```

Expected output:
```
Migrations for 'authorization':
  apps/authorization/migrations/0002_service_ui_fields.py
    - Add field display_order to service
    - Add field icon_class to service
    - Add field list_url_name to service
```

- [ ] **Step 2.2: Inspect the generated migration file**

Open `apps/authorization/migrations/0002_service_ui_fields.py` and confirm it contains three `AddField` operations — one each for `display_order`, `icon_class`, `list_url_name`. No destructive operations should be present.

- [ ] **Step 2.3: Apply migration**

```bash
python manage.py migrate
```

Expected: `Applying authorization.0002_service_ui_fields... OK`

- [ ] **Step 2.4: Run tests — confirm they now pass**

```bash
python manage.py test apps.authorization.tests -v 2
```

Expected: All tests pass. If any test fails, read the error carefully — the most common issue would be a URL reverse failing because the URL conf isn't loading. In that case, check `DJANGO_SETTINGS_MODULE` is set correctly in the test environment.

- [ ] **Step 2.5: Commit model, tests, and migration together**

```bash
git add apps/authorization/models.py apps/authorization/tests.py apps/authorization/migrations/0002_service_ui_fields.py
git commit -m "feat(authorization): add UI metadata fields and get_list_url to Service model"
```

---

## Task 3: Update Seed Command

**Files:**
- Modify: `apps/authorization/management/commands/seed_services.py`

---

- [ ] **Step 3.1: Update the seed command**

Open `apps/authorization/management/commands/seed_services.py`. The `SERVICE_DEFINITIONS` list currently has six entries. Update **only the two UI-visible entries** (`reports` and `segnalazioni`) to add the new keys. The other four entries (`core`, `reports_api`, `segnalazioni_api`, `profiles`) are left unchanged — their rows get empty string defaults from the migration.

Replace the `Reports` entry:
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
```

Replace the `Segnalazioni` entry:
```python
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

Also update the `handle` method to pass the new fields into `defaults`:

```python
service, created = Service.objects.update_or_create(
    app_label=svc_def["app_label"],
    defaults={
        "name": svc_def["name"],
        "description": svc_def.get("description", ""),
        "is_active": True,
        "icon_class": svc_def.get("icon_class", ""),
        "list_url_name": svc_def.get("list_url_name", ""),
        "display_order": svc_def.get("display_order", 0),
    },
)
```

- [ ] **Step 3.2: Run seed command and verify output**

```bash
python manage.py seed_services
```

Expected: 6 lines of output — `Updated: Reports (reports)` and `Updated: Segnalazioni (segnalazioni)` among them (or `Created` if running on a fresh DB).

- [ ] **Step 3.3: Verify in the shell that fields are set**

```bash
python manage.py shell -c "
from apps.authorization.models import Service
for s in Service.objects.all():
    print(s.app_label, repr(s.list_url_name), repr(s.icon_class), s.display_order)
"
```

Expected: `reports` has `'reports:report_list'` and `'fa-solid fa-file-invoice'`; `segnalazioni` has `'segnalazioni:segnalazioni_list'` and `'fa-solid fa-triangle-exclamation'`. Other services have `''` for both string fields.

- [ ] **Step 3.4: Commit seed command update**

```bash
git add apps/authorization/management/commands/seed_services.py
git commit -m "feat(authorization): add icon_class, list_url_name, display_order to seed definitions"
```

---

## Task 4: Update Home Page Template

**Files:**
- Modify: `templates/core/home.html`

---

- [ ] **Step 4.1: Replace hardcoded service cards with data-driven loop**

Open `templates/core/home.html`. The current file (lines 16–39) has a hardcoded `<div class="text-chunk">` section followed by a `<div class="grid-container columns-3">` with two hardcoded `<div class="grid-column">` cards.

Replace everything from `<div class="text-chunk">` to the closing `</div>` of the grid (lines 16–39) with:

```django
{% if accessible_services %}
<div class="text-chunk">
    <h1>Servizi</h1>
    <p>Elenco dei principali servizi disponibili.</p>
</div>

<!-- LAYOUT RESPONSIVE A 3 COLONNE -->
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

- [ ] **Step 4.2: Run tests to confirm nothing broke**

```bash
python manage.py test apps.authorization.tests -v 2
```

Expected: all tests still pass.

- [ ] **Step 4.3: Commit home page template**

```bash
git add templates/core/home.html
git commit -m "feat(core): render home page service cards dynamically from accessible_services"
```

---

## Task 5: Update Sidebar Template

**Files:**
- Modify: `templates/includes/sidebar.html`

---

- [ ] **Step 5.1: Replace hardcoded submenu with data-driven loop**

Open `templates/includes/sidebar.html`. Find the "Servizi" `<li>` block (lines 21–33 in the current file). It looks like:

```html
<li>
    <button onClick="toggleSubMenu(this)" class="dropdown-link">
        <svg ...>...</svg>
        <span>Servizi</span>
        <svg ...>...</svg>
    </button>
    <ul class="sub-menu">
        <div>
            <li><a href="{% url 'reports:report_list' %}">Report di sopralluogo</a></li>
            <li><a href="{% url 'segnalazioni:segnalazioni_list' %}">Segnalazioni</a></li>
        </div>
    </ul>
</li>
```

Replace the entire `<li>` block (keeping the SVG icons exactly as they are) with:

```django
{% if accessible_services %}
<li>
    <button onClick="toggleSubMenu(this)" class="dropdown-link">
        <svg xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px" fill="#e3e3e3"><path d="M520-600v-240h320v240H520ZM120-440v-400h320v400H120Zm400 320v-400h320v400H520Zm-400 0v-240h320v240H120Zm80-400h160v-240H200v240Zm400 320h160v-240H600v240Zm0-480h160v-80H600v80ZM200-200h160v-80H200v80Zm160-320Zm240-160Zm0 240ZM360-280Z"/></svg>
        <span>Servizi</span>
        <svg xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px" fill="#e8eaed"><path d="M480-344 240-584l56-56 184 184 184-184 56 56-240 240Z"/></svg>
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

- [ ] **Step 5.2: Run full test suite**

```bash
python manage.py test apps.authorization.tests -v 2
```

Expected: all tests pass.

- [ ] **Step 5.3: Commit sidebar template**

```bash
git add templates/includes/sidebar.html
git commit -m "feat(sidebar): render Servizi submenu dynamically from accessible_services"
```

---

## Manual Smoke Test (after all tasks complete)

Start the dev server and verify:

1. Log in as a user in `reports_users` only — home page shows only "Reports" card, sidebar shows only "Report di sopralluogo" link
2. Log in as a user in `managers` — home page shows both cards, sidebar shows both links
3. Log in as a user with no service groups — home page shows no "Servizi" section at all, sidebar shows no "Servizi" menu item
4. Log in as a superuser — home page shows both cards, sidebar shows both links

---

## Adding a New Service (future reference)

1. Implement the new Django app with its URL namespace
2. Add an entry to `SERVICE_DEFINITIONS` in `seed_services.py`:
   ```python
   {
       "name": "My New Service",
       "app_label": "my_app",          # must match the URL namespace
       "description": "Description shown on home card",
       "groups": ["my_group", "managers"],
       "icon_class": "fa-solid fa-icon-name",
       "list_url_name": "my_app:list",  # must be a registered URL name
       "display_order": 3,
   }
   ```
3. Run `python manage.py seed_services`
4. Done — the card and sidebar link appear automatically for users in `my_group` or `managers`
