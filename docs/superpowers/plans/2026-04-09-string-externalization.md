# String Externalization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Centralizzare tutte le stringhe UI visibili nei template HTML in `config/strings.py`, iniettate via context processor.

**Architecture:** Si crea `config/strings.py` con un flat dict `UI_STRINGS`, si aggiunge una funzione `ui_strings()` al context processor esistente `config/context_processors.py`, si registra in `config/settings.py`, e si aggiornano 8 template per usare `{{ ui_strings.<key> }}` al posto delle stringhe hardcoded. Il rendered output dei template non cambia — le stringhe restano le stesse, cambia solo l'origine.

**Tech Stack:** Django 6.0, Python, Django template language. Test runner: `uv run python manage.py test`.

---

## File Map

| Azione | File | Responsabilità |
|--------|------|----------------|
| Crea | `config/strings.py` | Dict `UI_STRINGS` con tutte le stringhe UI |
| Crea | `config/tests.py` | Test per context processor e strings |
| Modifica | `config/context_processors.py` | Aggiunge funzione `ui_strings()` |
| Modifica | `config/settings.py` | Registra il nuovo context processor |
| Modifica | `templates/includes/sidebar.html` | Usa `ui_strings.*` |
| Modifica | `templates/base.html` | Usa `ui_strings.*` |
| Modifica | `templates/core/home.html` | Usa `ui_strings.*` |
| Modifica | `templates/accounts/login.html` | Usa `ui_strings.*` |
| Modifica | `templates/reports/report_list.html` | Usa `ui_strings.*` |
| Modifica | `templates/reports/report_detail.html` | Usa `ui_strings.*` |
| Modifica | `templates/segnalazioni/segnalazioni_list.html` | Usa `ui_strings.*` |
| Modifica | `templates/profiles/profile.html` | Usa `ui_strings.*` |

---

## Task 1: Crea `config/strings.py` con test

**Files:**
- Create: `config/strings.py`
- Create: `config/tests.py`

- [ ] **Step 1.1: Scrivi il test (TDD — fallisce perché il file non esiste ancora)**

Crea `config/tests.py`:

```python
from django.test import TestCase
from config.strings import UI_STRINGS


class UIStringsTest(TestCase):
    """Verifica che UI_STRINGS contenga le chiavi attese."""

    def test_is_dict(self):
        self.assertIsInstance(UI_STRINGS, dict)

    def test_required_keys_present(self):
        required_keys = [
            # Comuni
            "loading", "actions_col", "error_title",
            # Nav
            "nav_home", "nav_documents", "nav_services",
            "nav_contacts", "nav_support", "nav_profile",
            "nav_logout", "nav_toggle_title",
            # Home
            "home_greeting", "home_welcome",
            "home_services_title", "home_services_subtitle", "home_goto_btn",
            # Login
            "login_title", "login_azure_btn", "login_divider",
            "login_admin_only", "login_username_label",
            "login_password_label", "login_submit_btn",
            # Reports
            "reports_page_title", "reports_page_subtitle",
            "reports_back_link", "reports_detail_prefix",
            "reports_pdf_btn", "reports_maps_btn", "reports_pdf_loading",
            # Segnalazioni
            "segnalazioni_page_title", "segnalazioni_page_subtitle",
            "segnalazioni_col_title", "segnalazioni_col_category",
            "segnalazioni_col_status", "segnalazioni_col_date",
            # Profilo
            "profile_page_title", "profile_field_username",
            "profile_field_email", "profile_field_fullname",
            "profile_field_joined",
        ]
        for key in required_keys:
            with self.subTest(key=key):
                self.assertIn(key, UI_STRINGS)

    def test_no_empty_values(self):
        for key, value in UI_STRINGS.items():
            with self.subTest(key=key):
                self.assertTrue(value, f"UI_STRINGS['{key}'] è vuoto")
```

- [ ] **Step 1.2: Esegui il test — deve fallire**

```bash
uv run python manage.py test config.tests.UIStringsTest -v 2
```

Atteso: `ImportError: cannot import name 'UI_STRINGS' from 'config.strings'` (o `ModuleNotFoundError`)

- [ ] **Step 1.3: Crea `config/strings.py`**

```python
"""
UI string definitions for the GIS Dashboard.

All user-visible text in templates is defined here.
To update a label, change the value — do not change the key (templates depend on it).
To find all usages of a key: grep -r "ui_strings\." templates/
"""

UI_STRINGS = {
    # --- Comuni ---
    "loading": "Caricamento...",
    "actions_col": "Azioni",
    "error_title": "Errore",

    # --- Navigazione (sidebar) ---
    "nav_home": "Home",
    "nav_documents": "Documenti",
    "nav_services": "Servizi",
    "nav_contacts": "Contatti",
    "nav_support": "Assistenza",
    "nav_profile": "Profilo",
    "nav_logout": "Logout",
    "nav_toggle_title": "Toggle sidebar",

    # --- Home ---
    "home_greeting": "Buongiorno",
    "home_welcome": "Ti diamo il benvenuto nell'area di gestione della reportistica di Milano Serravalle - Milano Tangenziali S.p.A.",
    "home_services_title": "Servizi",
    "home_services_subtitle": "Elenco dei servizi disponibili.",
    "home_goto_btn": "Vai alla pagina",

    # --- Login ---
    "login_title": "Login DT Serravalle",
    "login_azure_btn": "Accedi con Azure",
    "login_divider": "oppure",
    "login_admin_only": "Accesso riservato agli amministratori",
    "login_username_label": "Username",
    "login_password_label": "Password",
    "login_submit_btn": "Login",

    # --- Reports ---
    "reports_page_title": "Report di sopralluogo",
    "reports_page_subtitle": "Archivio dei sopralluoghi effettuati.",
    "reports_back_link": "Torna all'elenco",
    "reports_detail_prefix": "Dettaglio report #",
    "reports_pdf_btn": "Scarica PDF",
    "reports_maps_btn": "Apri in Google Maps",
    "reports_pdf_loading": "Generazione PDF in corso...",

    # --- Segnalazioni ---
    "segnalazioni_page_title": "Segnalazioni",
    "segnalazioni_page_subtitle": "Archivio delle segnalazioni ricevute.",
    "segnalazioni_col_title": "Titolo",
    "segnalazioni_col_category": "Categoria",
    "segnalazioni_col_status": "Stato",
    "segnalazioni_col_date": "Data",

    # --- Profilo ---
    "profile_page_title": "Profilo Utente",
    "profile_field_username": "Nome Utente",
    "profile_field_email": "Email",
    "profile_field_fullname": "Nome Completo",
    "profile_field_joined": "Data Registrazione",
}
```

- [ ] **Step 1.4: Esegui il test — deve passare**

```bash
uv run python manage.py test config.tests.UIStringsTest -v 2
```

Atteso: `OK` (3 test)

- [ ] **Step 1.5: Commit**

```bash
git add config/strings.py config/tests.py
git commit -m "feat: add UI_STRINGS dict in config/strings.py"
```

---

## Task 2: Context processor + registrazione settings

**Files:**
- Modify: `config/context_processors.py`
- Modify: `config/settings.py`
- Modify: `config/tests.py`

- [ ] **Step 2.1: Aggiungi test per il context processor (TDD — fallisce perché la funzione non esiste)**

Aggiungi in fondo a `config/tests.py`:

```python
from django.test import RequestFactory
from config.context_processors import ui_strings as ui_strings_processor
from config.strings import UI_STRINGS


class UIStringsContextProcessorTest(TestCase):
    """Verifica che il context processor inietti ui_strings."""

    def setUp(self):
        self.factory = RequestFactory()

    def test_returns_ui_strings_dict(self):
        request = self.factory.get('/')
        result = ui_strings_processor(request)
        self.assertIn("ui_strings", result)
        self.assertIs(result["ui_strings"], UI_STRINGS)
```

- [ ] **Step 2.2: Esegui il test — deve fallire**

```bash
uv run python manage.py test config.tests.UIStringsContextProcessorTest -v 2
```

Atteso: `ImportError: cannot import name 'ui_strings' from 'config.context_processors'`

- [ ] **Step 2.3: Aggiungi la funzione a `config/context_processors.py`**

Il file attuale contiene solo `csp_nonce`. Aggiungi in fondo:

```python
from config.strings import UI_STRINGS


def ui_strings(request):
    """Expose UI string definitions to all templates."""
    return {"ui_strings": UI_STRINGS}
```

- [ ] **Step 2.4: Esegui il test — deve passare**

```bash
uv run python manage.py test config.tests.UIStringsContextProcessorTest -v 2
```

Atteso: `OK`

- [ ] **Step 2.5: Registra il context processor in `config/settings.py`**

In `TEMPLATES[0]['OPTIONS']['context_processors']`, aggiungi dopo `'config.context_processors.csp_nonce'`:

```python
'config.context_processors.ui_strings',
```

La lista diventa:
```python
'context_processors': [
    'django.template.context_processors.request',
    'django.contrib.auth.context_processors.auth',
    'django.contrib.messages.context_processors.messages',
    'apps.authorization.context_processors.accessible_services',
    'config.context_processors.csp_nonce',
    'config.context_processors.ui_strings',
],
```

- [ ] **Step 2.6: Aggiungi test di integrazione — verifica che `ui_strings` arrivi ai template**

Aggiungi in fondo a `config/tests.py`:

```python
from django.contrib.auth.models import User
from apps.authorization.models import Service
from django.contrib.auth.models import Group


class UIStringsInTemplateContextTest(TestCase):
    """Verifica che ui_strings sia disponibile nel context dei template."""

    def setUp(self):
        self.user = User.objects.create_user("testuser_ctx", password="pass")
        group = Group.objects.create(name="core_group_ctx")
        self.user.groups.add(group)
        core_svc = Service.objects.create(
            name="Dashboard", app_label="core", is_active=True, display_order=0
        )
        core_svc.allowed_groups.set([group])
        self.client.force_login(self.user)

    def test_ui_strings_in_home_context(self):
        response = self.client.get('/')
        self.assertIn("ui_strings", response.context)

    def test_home_renders_greeting_from_ui_strings(self):
        response = self.client.get('/')
        self.assertContains(response, "Buongiorno")
```

- [ ] **Step 2.7: Esegui tutti i test di config**

```bash
uv run python manage.py test config -v 2
```

Atteso: `OK` (tutti i test passano)

- [ ] **Step 2.8: Commit**

```bash
git add config/context_processors.py config/settings.py config/tests.py
git commit -m "feat: register ui_strings context processor"
```

---

## Task 3: Aggiorna `sidebar.html` e `base.html`

**Files:**
- Modify: `templates/includes/sidebar.html`
- Modify: `templates/base.html`

- [ ] **Step 3.1: Esegui i test esistenti — devono passare (baseline)**

```bash
uv run python manage.py test -v 2
```

Atteso: tutti i test passano prima di toccare i template.

- [ ] **Step 3.2: Aggiorna `templates/includes/sidebar.html`**

Sostituzioni da fare (trova e sostituisci):

| Hardcoded | Sostituire con |
|-----------|---------------|
| `title="Toggle sidebar"` | `title="{{ ui_strings.nav_toggle_title }}"` |
| `<span>Home</span>` | `<span>{{ ui_strings.nav_home }}</span>` |
| `<span>Documenti</span>` | `<span>{{ ui_strings.nav_documents }}</span>` |
| `<span>Servizi</span>` (nel dropdown button) | `<span>{{ ui_strings.nav_services }}</span>` |
| `<span>Contatti</span>` | `<span>{{ ui_strings.nav_contacts }}</span>` |
| `<span>Assistenza</span>` | `<span>{{ ui_strings.nav_support }}</span>` |
| `<span>Profilo</span>` (entrambe le occorrenze) | `<span>{{ ui_strings.nav_profile }}</span>` |
| `<span>Logout</span>` (entrambe le occorrenze) | `<span>{{ ui_strings.nav_logout }}</span>` |

- [ ] **Step 3.3: `templates/base.html` — nessuna modifica necessaria**

Il `{% block title %}` di default (`GIS Dashboard`) non viene mai raggiunto: tutti i template figli sovrascrivono il block. Non è in `UI_STRINGS` e non va toccato.

- [ ] **Step 3.4: Esegui i test per verificare che nulla sia rotto**

```bash
uv run python manage.py test -v 2
```

Atteso: tutti i test passano

- [ ] **Step 3.5: Commit**

```bash
git add templates/includes/sidebar.html templates/base.html
git commit -m "feat: externalize strings in sidebar and base templates"
```

---

## Task 4: Aggiorna `home.html` e `login.html`

**Files:**
- Modify: `templates/core/home.html`
- Modify: `templates/accounts/login.html`

- [ ] **Step 4.1: Aggiorna `templates/core/home.html`**

| Hardcoded | Sostituire con |
|-----------|---------------|
| `<h2>Buongiorno {{ user.first_name\|default:user.username }}!</h2>` | `<h2>{{ ui_strings.home_greeting }} {{ user.first_name\|default:user.username }}!</h2>` |
| `<p>Ti diamo il benvenuto nell'area di gestione della reportistica di Milano Serravalle - Milano Tangenziali S.p.A.</p>` | `<p>{{ ui_strings.home_welcome }}</p>` |
| `<h1>Servizi</h1>` | `<h1>{{ ui_strings.home_services_title }}</h1>` |
| `<p>Elenco dei servizi disponibili.</p>` | `<p>{{ ui_strings.home_services_subtitle }}</p>` |
| `Vai alla pagina` (nel link) | `{{ ui_strings.home_goto_btn }}` |

- [ ] **Step 4.2: Aggiorna `templates/accounts/login.html`**

| Hardcoded | Sostituire con |
|-----------|---------------|
| `<h1>Login DT Serravalle</h1>` | `<h1>{{ ui_strings.login_title }}</h1>` |
| `Accedi con Azure` (testo del bottone) | `{{ ui_strings.login_azure_btn }}` |
| `<span>oppure</span>` | `<span>{{ ui_strings.login_divider }}</span>` |
| `<p class="admin-only-label">Accesso riservato agli amministratori</p>` | `<p class="admin-only-label">{{ ui_strings.login_admin_only }}</p>` |
| `<label class="form-label" for="username">Username</label>` | `<label class="form-label" for="username">{{ ui_strings.login_username_label }}</label>` |
| `<label class="form-label" for="password">Password</label>` | `<label class="form-label" for="password">{{ ui_strings.login_password_label }}</label>` |
| `<button class="btn blue" type="submit">Login</button>` | `<button class="btn blue" type="submit">{{ ui_strings.login_submit_btn }}</button>` |

Nota: `login.html` non estende `base.html` e non riceve il context processor automaticamente — **riceve** il context processor perché Django lo applica a tutte le view che restituiscono un `TemplateResponse` o usano `render()`. Verificare nella step successiva.

- [ ] **Step 4.3: Esegui i test**

```bash
uv run python manage.py test -v 2
```

Atteso: tutti i test passano

- [ ] **Step 4.4: Commit**

```bash
git add templates/core/home.html templates/accounts/login.html
git commit -m "feat: externalize strings in home and login templates"
```

---

## Task 5: Aggiorna `report_list.html` e `report_detail.html`

**Files:**
- Modify: `templates/reports/report_list.html`
- Modify: `templates/reports/report_detail.html`

- [ ] **Step 5.1: Aggiorna `templates/reports/report_list.html`**

| Hardcoded | Sostituire con |
|-----------|---------------|
| `<h1><i class="fa-solid fa-file-lines"></i> Report di sopralluogo</h1>` | `<h1><i class="fa-solid fa-file-lines"></i> {{ ui_strings.reports_page_title }}</h1>` |
| `<p>Archivio dei sopralluoghi effettuati.</p>` | `<p>{{ ui_strings.reports_page_subtitle }}</p>` |
| `<th>Azioni</th>` | `<th>{{ ui_strings.actions_col }}</th>` |
| `Caricamento...` (nel `<td>`) | `{{ ui_strings.loading }}` |
| `<p style="...">Generazione PDF in corso...</p>` | `<p style="...">{{ ui_strings.reports_pdf_loading }}</p>` |

- [ ] **Step 5.2: Aggiorna `templates/reports/report_detail.html`**

| Hardcoded | Sostituire con |
|-----------|---------------|
| `Torna all'elenco` (nel link) | `{{ ui_strings.reports_back_link }}` |
| `<h1>Errore</h1>` | `<h1>{{ ui_strings.error_title }}</h1>` |
| `<h1>Dettaglio report #{{ object_id }}</h1>` | `<h1>{{ ui_strings.reports_detail_prefix }}{{ object_id }}</h1>` |
| `Scarica PDF` (nel bottone) | `{{ ui_strings.reports_pdf_btn }}` |
| `Apri in Google Maps` (nel link) | `{{ ui_strings.reports_maps_btn }}` |

- [ ] **Step 5.3: Esegui i test**

```bash
uv run python manage.py test -v 2
```

Atteso: tutti i test passano

- [ ] **Step 5.4: Commit**

```bash
git add templates/reports/report_list.html templates/reports/report_detail.html
git commit -m "feat: externalize strings in reports templates"
```

---

## Task 6: Aggiorna `segnalazioni_list.html` e `profile.html`

**Files:**
- Modify: `templates/segnalazioni/segnalazioni_list.html`
- Modify: `templates/profiles/profile.html`

- [ ] **Step 6.1: Aggiorna `templates/segnalazioni/segnalazioni_list.html`**

| Hardcoded | Sostituire con |
|-----------|---------------|
| `<h1><i class="fa-solid fa-triangle-exclamation"></i> Segnalazioni</h1>` | `<h1><i class="fa-solid fa-triangle-exclamation"></i> {{ ui_strings.segnalazioni_page_title }}</h1>` |
| `<p>Archivio delle segnalazioni ricevute.</p>` | `<p>{{ ui_strings.segnalazioni_page_subtitle }}</p>` |
| `<th data-sort="titolo">Titolo</th>` | `<th data-sort="titolo">{{ ui_strings.segnalazioni_col_title }}</th>` |
| `<th data-sort="categoria">Categoria</th>` | `<th data-sort="categoria">{{ ui_strings.segnalazioni_col_category }}</th>` |
| `<th data-sort="stato">Stato</th>` | `<th data-sort="stato">{{ ui_strings.segnalazioni_col_status }}</th>` |
| `<th data-sort="data">Data</th>` | `<th data-sort="data">{{ ui_strings.segnalazioni_col_date }}</th>` |
| `<th>Azioni</th>` | `<th>{{ ui_strings.actions_col }}</th>` |
| `Caricamento...` (nel `<td>`) | `{{ ui_strings.loading }}` |

- [ ] **Step 6.2: Aggiorna `templates/profiles/profile.html`**

| Hardcoded | Sostituire con |
|-----------|---------------|
| `{% block title %}Profilo Utente - GIS Dashboard{% endblock %}` | `{% block title %}{{ ui_strings.profile_page_title }} - GIS Dashboard{% endblock %}` |
| `<th>Nome Utente</th>` | `<th>{{ ui_strings.profile_field_username }}</th>` |
| `<th>Email</th>` | `<th>{{ ui_strings.profile_field_email }}</th>` |
| `<th>Nome Completo</th>` | `<th>{{ ui_strings.profile_field_fullname }}</th>` |
| `<th>Data Registrazione</th>` | `<th>{{ ui_strings.profile_field_joined }}</th>` |

- [ ] **Step 6.3: Esegui tutti i test**

```bash
uv run python manage.py test -v 2
```

Atteso: tutti i test passano

- [ ] **Step 6.4: Commit**

```bash
git add templates/segnalazioni/segnalazioni_list.html templates/profiles/profile.html
git commit -m "feat: externalize strings in segnalazioni and profile templates"
```

---

## Task 7: Verifica finale

- [ ] **Step 7.1: Esegui la suite completa di test**

```bash
uv run python manage.py test -v 2
```

Atteso: tutti i test passano, nessun errore.

- [ ] **Step 7.2: Avvia il server e verifica manualmente**

```bash
uv run python manage.py runserver
```

Naviga su:
- `/` — home page: verifica greeting, welcome message, titolo sezione Servizi
- `/auth/login/` — pagina login: verifica titolo, bottone Azure, label form
- Sidebar: verifica tutte le voci di menu

- [ ] **Step 7.3: Verifica che nessuna stringa hardcoded sia rimasta nei template in scope**

```bash
grep -rn "Buongiorno\|Caricamento\|Accedi con Azure\|Torna all'elenco\|Scarica PDF\|Nome Utente\|Data Registrazione" templates/
```

Atteso: nessun risultato (tutte le occorrenze sono state sostituite).
