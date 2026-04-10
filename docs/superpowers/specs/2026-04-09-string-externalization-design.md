# String Externalization — Design Spec

**Data:** 2026-04-09  
**Branch:** `feat/string-externalization`  
**Stato:** Approvato

---

## Obiettivo

Centralizzare tutte le stringhe UI visibili nei template HTML in un unico file Python. L'app rimane monolingua (italiano); la motivazione è la manutenibilità: aggiornare un testo richiede una sola modifica in un unico posto.

---

## Approccio scelto

**Flat dict `UI_STRINGS` in `config/strings.py`**, iniettato globalmente nei template tramite un context processor Django. Le stringhe condivise tra più template vengono definite una volta sola.

Approcci scartati:
- *Costanti individuali*: impraticabili per l'iniezione nei template (richiederebbero import espliciti di ogni costante nel context processor).
- *Dict annidati*: Django templates non supportano nativamente l'accesso annidato; richiederebbe un template filter custom senza benefici reali.
- *File per-app*: overkill per questo progetto; le stringhe condivise (sidebar, base) non appartengono a nessuna app specifica.

---

## Struttura dei file

### File nuovo

```
config/strings.py   ← accanto a settings.py, context_processors.py
```

### File modificati

```
config/context_processors.py   ← aggiunta funzione ui_strings()
config/settings.py              ← registrazione del context processor
templates/**/*.html             ← sostituzione stringhe hardcoded
```

---

## `config/strings.py`

Dizionario flat con commenti di sezione. Naming convention: `<sezione>_<elemento>` per le stringhe specifiche; nomi semplici per le stringhe comuni.

```python
"""
UI string definitions for the GIS Dashboard.

All user-visible text in templates is defined here.
To update a label, change the value — do not change the key (templates depend on it).
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

---

## Context processor

Aggiunta in `config/context_processors.py` (file esistente, già contiene `csp_nonce`):

```python
from config.strings import UI_STRINGS

def ui_strings(request):
    return {"ui_strings": UI_STRINGS}
```

Registrazione in `config/settings.py` (in `TEMPLATES[0]['OPTIONS']['context_processors']`):

```python
"config.context_processors.ui_strings",
```

---

## Uso nei template

La variabile `ui_strings` è disponibile in tutti i template automaticamente (tramite `RequestContext`).

**Stringa semplice:**
```html
<!-- Prima -->
<span>Logout</span>
<!-- Dopo -->
<span>{{ ui_strings.nav_logout }}</span>
```

**Stringa con variabile dinamica:**
```html
<!-- Prima -->
<h2>Buongiorno {{ user.first_name }}!</h2>
<!-- Dopo -->
<h2>{{ ui_strings.home_greeting }} {{ user.first_name }}!</h2>
```

La parte fissa va in `ui_strings`, quella dinamica rimane variabile template — nessun workaround necessario.

---

## Scope dell'implementazione

### Template da aggiornare

| Template | Stringhe chiave da esternalizzare |
|---|---|
| `templates/base.html` | titolo default |
| `templates/includes/sidebar.html` | voci menu, toggle title |
| `templates/core/home.html` | greeting, welcome, titoli sezione, bottone |
| `templates/accounts/login.html` | titolo, bottoni, label form |
| `templates/reports/report_list.html` | titolo, sottotitolo, loading, colonne |
| `templates/reports/report_detail.html` | back link, titoli, bottoni |
| `templates/segnalazioni/segnalazioni_list.html` | titolo, sottotitolo, colonne, loading |
| `templates/profiles/profile.html` | titolo, label tabella |

### Fuori scope

- `templates/reports/report_pdf.html` — renderizzato via `render_to_string` con dict plain (non `RequestContext`); i context processor non vengono eseguiti. Le stringhe del PDF rimangono hardcoded.
- Stringhe nei file `.py` (log, messaggi di errore interni, seed)
- Field labels ArcGIS in `apps/reports/mappings.py` (già centralizzate)
- Stringhe tecniche nei template (attributi `data-*`, classi CSS, nomi URL)
- Testi iniettati via JavaScript (gestiti separatamente nei file `.js`)

---

## Note implementative

- Non modificare le chiavi esistenti senza cercare tutti i template che le usano: `grep -r "ui_strings\." templates/`
- Per aggiungere stringhe di una nuova app: aggiungere una sezione con commento in `config/strings.py`. Non serve toccare il context processor.
