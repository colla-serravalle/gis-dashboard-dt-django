# Segnalazioni Service — Implementation Brief for Claude Code

**Date:** 2026-03-11
**Branch:** `feature/segnalazioni`

---

## Context & Architecture

Add a new **"Segnalazioni"** service to the GIS Dashboard: a paginated, filterable list view of citizen/staff reports sourced from ArcGIS (integration is stubbed with a TODO). The app mirrors the existing `reports` app pattern and is wired into the project's authorization workflow (Azure AD → Django Groups → Service access).

**Tech stack:** Django CBV, `login_required`, `JsonResponse`, existing `filter-manager.js` / `table-sorter.js` frontend JS, `seed_services` management command.

---

## File Map (all changes at a glance)

| Action   | Path |
|----------|------|
| Create   | `apps/segnalazioni/__init__.py` |
| Create   | `apps/segnalazioni/apps.py` |
| Create   | `apps/segnalazioni/views/__init__.py` |
| Create   | `apps/segnalazioni/views/api.py` |
| Create   | `apps/segnalazioni/urls.py` |
| Create   | `apps/segnalazioni/api_urls.py` |
| Create   | `templates/segnalazioni/segnalazioni_list.html` |
| Modify   | `config/settings.py` — INSTALLED_APPS |
| Modify   | `config/urls.py` — page + API routes |
| Modify   | `templates/core/home.html` — add card |
| Modify   | `apps/authorization/management/commands/seed_services.py` |

---

## Task 1 — App scaffold

### `apps/segnalazioni/__init__.py`
Empty file.

### `apps/segnalazioni/apps.py`
```python
from django.apps import AppConfig


class SegnalazioniConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.segnalazioni'
    label = 'segnalazioni'
```

### `config/settings.py`
In `INSTALLED_APPS`, add after `'apps.reports'`:
```python
    'apps.segnalazioni',
```

**Verify:** `python manage.py check` → `System check identified no issues (0 silenced).`

---

## Task 2 — Page view & URL config

### `apps/segnalazioni/views/__init__.py`
```python
"""Page views for segnalazioni app."""

from django.shortcuts import render
from django.views import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator


@method_decorator(login_required, name='dispatch')
class SegnalazioniListView(View):
    """Segnalazioni list view with filtering, sorting, and pagination."""

    template_name = 'segnalazioni/segnalazioni_list.html'

    def get(self, request):
        from django.conf import settings
        context = {
            'items_per_page': getattr(settings, 'ITEMS_PER_PAGE', 10),
        }
        return render(request, self.template_name, context)
```

### `apps/segnalazioni/urls.py`
```python
"""URL configuration for segnalazioni app - page views."""

from django.urls import path
from .views import SegnalazioniListView

app_name = 'segnalazioni'

urlpatterns = [
    path('segnalazioni/', SegnalazioniListView.as_view(), name='segnalazioni_list'),
]
```

---

## Task 3 — Stub API view & API URL config

### `apps/segnalazioni/views/api.py`
```python
"""API views for segnalazioni app — stub implementation.

TODO: Replace stub with real ArcGIS integration.
Configure the following in settings.py or .env:
  - SEGNALAZIONI_ARCGIS_LAYER_URL: URL of the ArcGIS feature layer
  - SEGNALAZIONI_FIELD_MAP: dict mapping ArcGIS field names to display labels
Then call query_feature_layer() from apps.core.services.arcgis,
following the pattern in apps/reports/views/api.py.
"""

import logging
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)


@login_required
@require_GET
def get_data(request):
    """
    Get paginated segnalazioni data.

    TODO: Replace with real ArcGIS query (see module docstring).
    """
    return JsonResponse({'data': [], 'total': 0})


@login_required
@require_GET
def get_filter_options(request):
    """
    Get available filter options for segnalazioni dropdowns.

    TODO: Replace with real ArcGIS query (see module docstring).
    """
    return JsonResponse({})
```

### `apps/segnalazioni/api_urls.py`
```python
"""URL configuration for segnalazioni app - API views."""

from django.urls import path
from .views.api import get_data, get_filter_options

app_name = 'segnalazioni_api'

urlpatterns = [
    path('data/', get_data, name='get_data'),
    path('filters/', get_filter_options, name='get_filters'),
]
```

### `config/urls.py`
Add after the `reports` URL includes:
```python
    path('', include('apps.segnalazioni.urls')),
    path('segnalazioni/api/', include('apps.segnalazioni.api_urls')),
```

**Verify:** `python manage.py show_urls | grep segnalazioni` → should list `/segnalazioni/` and `/segnalazioni/api/data/` and `/segnalazioni/api/filters/`.

---

## Task 4 — List template

### `templates/segnalazioni/segnalazioni_list.html`

Adapt from `reports/report_list.html`. Key specifics:
- Columns: `#`, `Titolo`, `Categoria`, `Stato`, `Data`, `Azioni`
- Data endpoint: `/segnalazioni/api/data/`
- Filter options endpoint: `/segnalazioni/api/filters/`
- FilterManager filters: `categoria` (select), `stato` (select), `date_range` (dateRange)
- TableSorter sortable columns: `titolo` (col 1), `categoria` (col 2), `stato` (col 3), `data` (col 4)
- Default sort: `{ by: 'data', order: 'desc' }`
- Row fields from API: `row.id`, `row.titolo`, `row.categoria`, `row.stato`, `row.data`
- Empty state message: `Nessun dato trovato`
- Action icon: `fa-solid fa-eye` with `title="Apri Segnalazione"`

```html
{% extends 'base.html' %}
{% load static %}

{% block title %}Segnalazioni{% endblock %}

{% block content %}
<div class="content-header">
    <h1><i class="fa-solid fa-triangle-exclamation"></i> Segnalazioni</h1>
</div>

<div id="filters-container"></div>

<div class="table-container">
    <table>
        <thead>
            <tr>
                <th>#</th>
                <th data-sort="titolo">Titolo</th>
                <th data-sort="categoria">Categoria</th>
                <th data-sort="stato">Stato</th>
                <th data-sort="data">Data</th>
                <th>Azioni</th>
            </tr>
        </thead>
        <tbody id="tableBody">
            <tr><td colspan="6" style="text-align: center; padding: 20px;">Caricamento...</td></tr>
        </tbody>
    </table>
</div>

<div class="pagination-controls">
    <button id="prevPage" class="page-btn"><i class="fa-solid fa-circle-left fa-1x"></i></button>
    <span id="pageInfo">Pagina 1 di 1</span>
    <button id="nextPage" class="page-btn"><i class="fa-solid fa-circle-right fa-1x"></i></button>
</div>

<script>
    const itemsPerPage = {{ items_per_page }};

    let currentPage = 1;
    let totalItems = 0;
    let filterManager;
    let tableSorter;
    let currentSort = { by: 'data', order: 'desc' };

    window.currentSort = currentSort;

    function loadData(page, useFilters = false) {
        let url = `/segnalazioni/api/data/?page=${page}&per_page=${itemsPerPage}`;
        url += `&sort_by=${currentSort.by}&sort_order=${currentSort.order}`;

        if (useFilters && filterManager) {
            const filters = filterManager.getActiveFilters();
            const params = new URLSearchParams(filters);
            if (params.toString()) url += '&' + params.toString();
        }

        return fetch(url)
            .then(res => {
                if (!res.ok) throw new Error('Errore nel caricamento dei dati');
                return res.json();
            })
            .then(response => { updateTable(response, page); return response; })
            .catch(error => {
                console.error('Errore:', error);
                document.getElementById('tableBody').innerHTML =
                    '<tr><td colspan="6" style="text-align:center;padding:20px;color:red;">Errore nel caricamento dei dati</td></tr>';
                throw error;
            });
    }

    function updateTable(response, page) {
        const tbody = document.getElementById('tableBody');
        totalItems = response.total;
        const data = response.data;
        currentPage = page;

        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:20px;">Nessun dato trovato</td></tr>';
            updatePaginationControls();
            return;
        }

        tbody.innerHTML = '';
        data.forEach(row => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${escapeHtml(String(row.id ?? ''))}</td>
                <td>${escapeHtml(row.titolo ?? '')}</td>
                <td>${escapeHtml(row.categoria ?? '')}</td>
                <td>${escapeHtml(row.stato ?? '')}</td>
                <td>${escapeHtml(row.data ?? '')}</td>
                <td>
                    <div class="action-cell">
                        <a href="#" class="link-tabella action-icon-only" title="Apri Segnalazione">
                            <i class="fa-solid fa-eye"></i>
                        </a>
                    </div>
                </td>
            `;
            tbody.appendChild(tr);
        });
        updatePaginationControls();
    }

    function updatePaginationControls() {
        const totalPages = Math.ceil(totalItems / itemsPerPage);
        document.getElementById('pageInfo').textContent = `Pagina ${currentPage} di ${totalPages || 1}`;
        document.getElementById('prevPage').disabled = currentPage === 1;
        document.getElementById('nextPage').disabled = currentPage === totalPages || totalPages === 0;
    }

    document.getElementById('prevPage').addEventListener('click', () => {
        if (currentPage > 1) {
            filterManager ? filterManager.reloadData(currentPage - 1, itemsPerPage) : loadData(currentPage - 1);
        }
    });

    document.getElementById('nextPage').addEventListener('click', () => {
        const totalPages = Math.ceil(totalItems / itemsPerPage);
        if (currentPage < totalPages) {
            filterManager ? filterManager.reloadData(currentPage + 1, itemsPerPage) : loadData(currentPage + 1);
        }
    });

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    document.addEventListener('DOMContentLoaded', function () {
        tableSorter = new TableSorter({
            tableSelector: 'table',
            defaultSort: { by: 'data', order: 'desc' },
            sortableColumns: {
                1: { field: 'titolo' },
                2: { field: 'categoria' },
                3: { field: 'stato' },
                4: { field: 'data' }
            },
            onSortChange: function (field, order) {
                currentSort = { by: field, order: order };
                window.currentSort = currentSort;
                filterManager ? filterManager.reloadData(1, itemsPerPage) : loadData(1);
            }
        });

        filterManager = new FilterManager({
            containerId: 'filters-container',
            dataEndpoint: '/segnalazioni/api/data/',
            filterOptionsEndpoint: '/segnalazioni/api/filters/',
            itemsPerPage: itemsPerPage,
            filters: [
                { field: 'categoria',  label: 'Categoria', type: 'select' },
                { field: 'stato',      label: 'Stato',     type: 'select' },
                { field: 'date_range', label: 'Periodo',   type: 'dateRange' }
            ],
            onDataLoad: (data, page) => { updateTable(data, page); }
        });

        loadData(1);
    });
</script>
{% endblock %}
```

---

## Task 5 — Home page shortcut card

### `templates/core/home.html`

In the `.grid-container.columns-3` div, add after the "Report di sopralluogo" card block:

```html
<div class="grid-column">
    <div class="icon-background">
        <i class="fa-solid fa-triangle-exclamation fa-3x"></i>
    </div>
    <h2>Segnalazioni</h2>
    <p>Archivio delle segnalazioni ricevute.</p>
    <a href="{% url 'segnalazioni:segnalazioni_list' %}" class="standard-link filled-link">Vai alla pagina</a>
</div>
```

---

## Task 6 — Authorization seed

### `apps/authorization/management/commands/seed_services.py`

In `SERVICE_DEFINITIONS`, add after the `"Reports API"` entry:

```python
    {
        "name": "Segnalazioni",
        "app_label": "segnalazioni",
        "description": "Citizen/staff reports list",
        "groups": ["segnalazioni_users", "managers"],
    },
    {
        "name": "Segnalazioni API",
        "app_label": "segnalazioni_api",
        "description": "Segnalazioni JSON API endpoints",
        "groups": ["segnalazioni_users", "managers"],
    },
```

**Run after modifying:**
```bash
python manage.py seed_services
```
Expected output includes lines for `Created group: segnalazioni_users`, `Created: Segnalazioni`, `Created: Segnalazioni API`.

---

## Final verification checklist

- [ ] `python manage.py check` — no issues
- [ ] `python manage.py show_urls | grep segnalazioni` — three routes visible
- [ ] `/segnalazioni/` loads and shows "Nessun dato trovato" (stub)
- [ ] Home page shows the Segnalazioni card
- [ ] Django admin `/admin/authorization/service/` shows both new service entries

---

## Out of scope (future)

- Detail view for individual segnalazioni
- PDF export
- Real ArcGIS field mapping — see TODO in `apps/segnalazioni/views/api.py`
