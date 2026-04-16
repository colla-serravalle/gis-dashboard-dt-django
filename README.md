# Reports Serravalle

Internal dashboard for managing and viewing field inspection reports, built with Django. Connects to ArcGIS Enterprise to query feature layers, display report data with filtering/pagination, and proxy attachment images.

Migrated from a PHP application originally hosted on altervista.org.

## Features

- **Report Management** - Browse, filter, and search field inspection reports with pagination
- **Report Detail View** - Comprehensive view of individual reports with location data, operator information, and inspection details
- **PDF Export** - Generate PDF reports with company branding, signatures, and embedded photos
- **ArcGIS Integration** - Real-time data synchronization with ArcGIS Enterprise feature layers
- **Image Proxy** - Secure proxying of ArcGIS attachment images with automatic EXIF orientation correction
- **User Profiles** - Authenticated user profile pages with avatar support
- **Token Caching** - Intelligent ArcGIS token management with automatic refresh
- **Service Authorization** - Group-based access control per app/service with middleware enforcement and admin management
- **pgAdmin** - Web-based PostgreSQL management UI, accessible only from the internal subnet (`172.20.0.0/16`) via Nginx reverse proxy

## Tech Stack

- **Python** 3.13+
- **Django** 6.0.2 (ASGI/WSGI ready)
- **ArcGIS Enterprise** REST API (feature layers, tokens, attachments)
- **SQLite** (local auth/session storage)
- **xhtml2pdf** 0.2.16+ (PDF generation)
- **Pillow** 11.0.0+ (image processing and EXIF handling)
- **uv** (package manager)

## Project Structure

```
gis-dashboard-dt-parent/
├── config/                # Django project configuration
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py           # ASGI server configuration
│   └── wsgi.py           # WSGI server configuration
├── apps/
│   ├── accounts/          # Authentication (login/logout)
│   ├── core/              # Shared services and homepage
│   │   └── services/
│   │       └── arcgis.py  # ArcGIS REST API client with token caching
│   ├── profiles/          # User profile pages
│   │   ├── views.py       # Profile view
│   │   └── urls.py
│   ├── authorization/     # Service-level access control
│   │   ├── models.py      # Service model (app_label → groups mapping)
│   │   ├── middleware.py  # ServiceAccessMiddleware (request-level enforcement)
│   │   ├── decorators.py  # @require_service view decorator
│   │   ├── context_processors.py  # Injects accessible services into templates
│   │   ├── admin.py       # Admin UI for managing services and groups
│   │   └── management/commands/seed_services.py  # Seed/update service definitions
│   └── reports/           # Main application
│       ├── mappings.py    # Field labels and coded value mappings
│       ├── services/      # Business logic services
│       │   ├── image_utils.py   # Image fetching and processing
│       │   └── report_data.py   # Report data aggregation
│       ├── views/
│       │   ├── pages.py   # Page views (list, detail)
│       │   ├── api.py     # JSON API endpoints
│       │   └── pdf.py     # PDF export view
│       ├── urls.py        # Page URL routes
│       └── api_urls.py    # API URL routes
├── templates/             # Django HTML templates
├── static/                # CSS, JS, images
├── docs/                  # Documentation and design plans
├── logs/                  # Application logs (django.log)
├── manage.py
└── pyproject.toml
```

## Setup

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager
- ArcGIS Enterprise credentials with access to the feature service

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd gis-dashboard-dt-parent
   ```

2. Install dependencies:
   ```bash
   uv sync
   ```

   > **Note:** If you are behind a corporate proxy or firewall with SSL inspection, use `uv sync --native-tls` to use the system certificate store.

3. Create the environment file:
   ```bash
   cp .env.example .env
   ```

4. Edit `.env` with your configuration:
   ```
   SECRET_KEY=<generate-a-secret-key>
   DEBUG=True
   ALLOWED_HOSTS=localhost,127.0.0.1

   ARCGIS_USERNAME=<your-arcgis-username>
   ARCGIS_PASSWORD=<your-arcgis-password>
   ARCGIS_REFERER=https://dtserravalle.altervista.org/
   ```

5. Run database migrations and create a superuser:
   ```bash
   uv run python manage.py migrate
   uv run python manage.py createsuperuser
   ```

6. Seed services and groups:
   ```bash
   uv run python manage.py seed_services
   ```

   This creates the `Service` records (Dashboard, Reports, Reports API, Profiles) and their associated Django groups (`dashboard_users`, `reports_users`, `managers`). Assign users to the appropriate groups via the Django admin.

7. Start the development server:
   ```bash
   uv run python manage.py runserver
   uv run python manage.py runserver_plus --cert-file .certs/localhost.pem --key-file .certs/localhost.key 0.0.0.0:8443
   ```

   The application will be available at http://127.0.0.1:8000/

### VS Code

A launch configuration is provided in `.vscode/launch.json`. Press **F5** to start the server with the debugger attached. Make sure the Python interpreter is set to `.venv/Scripts/python.exe` (Ctrl+Shift+P > Python: Select Interpreter).

## URL Routes

### Pages

| URL | Description |
|---|---|
| `/` | Home page |
| `/reports/` | Report list with filtering and pagination |
| `/reports/detail/?id=<uniquerowid>` | Report detail view |
| `/reports/pdf/?rowid=<uniquerowid>` | Export report as PDF |
| `/profiles/` | User profile page (login required) |
| `/auth/login/` | Login page |
| `/auth/logout/` | Logout |
| `/app-control-panel/` | Django admin panel |

### API Endpoints

All API endpoints require authentication.

| URL | Method | Description |
|---|---|---|
| `/api/data/` | GET | Paginated report data with filtering and sorting |
| `/api/filters/` | GET | Available filter options for dropdowns |
| `/api/image/<layer>/<object_id>/<attachment_id>/` | GET | Proxy for ArcGIS attachment images |

#### Query Parameters for `/api/data/`

| Parameter | Default | Description |
|---|---|---|
| `page` | 1 | Page number |
| `per_page` | 10 | Items per page |
| `sort_by` | `data_rilevamento` | Field to sort by |
| `sort_order` | `desc` | Sort direction (`asc` or `desc`) |
| `nome_operatore` | - | Filter by operator |
| `tratta` | - | Filter by route |
| `tipologia_appalto` | - | Filter by contract type |
| `date_from` | - | Start date filter (YYYY-MM-DD) |
| `date_to` | - | End date filter (YYYY-MM-DD) |

## Environment Variables

See [.env.example](.env.example) for all available configuration options:

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | Yes | Django secret key |
| `DEBUG` | No | Enable debug mode (default: `True`) |
| `ALLOWED_HOSTS` | No | Comma-separated allowed hosts |
| `ARCGIS_USERNAME` | Yes | ArcGIS Enterprise portal username |
| `ARCGIS_PASSWORD` | Yes | ArcGIS Enterprise portal password |
| `ARCGIS_PORTAL_TOKEN_URL` | No | Token generation endpoint |
| `ARCGIS_FEATURE_SERVICE_URL` | No | Feature service base URL |
| `ARCGIS_REFERER` | No | Referer for token binding |
| `ARCGIS_TOKEN_EXPIRATION_MINUTES` | No | Token TTL in minutes (default: `60`) |
| `SESSION_TIMEOUT` | No | Session timeout in seconds (default: `3600`) |
| `ITEMS_PER_PAGE` | No | Default pagination size (default: `10`) |
| `MAX_LOGIN_ATTEMPTS` | No | Login attempts before lockout (default: `5`) |
| `LOCKOUT_DURATION` | No | Lockout duration in seconds (default: `900`) |

## Architecture

### ArcGIS Integration

The `apps/core/services/arcgis.py` module provides an `ArcGISService` class that handles:

- **Token management** - Generates and caches authentication tokens using Django's cache framework. Tokens are cached for their full lifetime minus 1 minute.
- **Feature layer queries** - Queries ArcGIS feature layers with configurable WHERE clauses and field selection.
- **Attachment retrieval** - Fetches attachment metadata and binary content for feature images.
- **SSL** - Uses `truststore` to delegate SSL verification to the OS certificate store, ensuring compatibility with corporate proxies and internal CAs.

### PDF Export

The `apps/reports/views/pdf.py` module handles report PDF generation using xhtml2pdf:

- **Template-based rendering** - Uses Django templates for consistent PDF layout
- **Embedded images** - Converts ArcGIS attachments and static assets to base64-encoded data URIs
- **EXIF orientation** - Automatically corrects photo orientation using Pillow's EXIF processing
- **Parallel fetching** - Uses ThreadPoolExecutor to fetch multiple photos concurrently
- **Branding** - Includes company logo, operator signature, and formatted report data

### Service Authorization

The `apps/authorization/` app implements group-based service access control:

- **`Service` model** - Maps a URL namespace (`app_label`) to one or more Django `Group`s. Superusers bypass all checks.
- **`ServiceAccessMiddleware`** - Resolves each incoming request to its URL namespace and checks that the authenticated user belongs to an allowed group. Returns `403 Forbidden` on failure. Configurable exempt apps and URL prefixes via settings (`SERVICE_AUTH_EXEMPT_APPS`, `SERVICE_AUTH_EXEMPT_URLS`).
- **`@require_service` decorator** - View-level alternative for cross-app service checks.
- **Context processor** - Injects the list of services accessible to the current user into every template context (`accessible_services`).
- **`seed_services` command** - Idempotent management command that creates or updates `Service` records and their groups from a central definition list.

Default services and groups seeded by `seed_services`:

| Service | App Label | Groups |
|---|---|---|
| Dashboard | `core` | `dashboard_users`, `managers` |
| Reports | `reports` | `reports_users`, `managers` |
| Reports API | `reports_api` | `reports_users`, `managers` |
| Profiles | `profiles` | `dashboard_users`, `reports_users`, `managers` |

The default policy when no `Service` record exists for an app is configurable via `SERVICE_AUTH_DEFAULT_POLICY` (`"allow"` or `"deny"`, default `"deny"`).

### Field Mappings

I campi a scelta multipla del feature layer ArcGIS contengono codici brevi (es. `pavimentazioni`). Il sistema li traduce in etichette leggibili (es. `Pavimentazioni`) leggendo i CSV delle liste scelte pubblicati su ArcGIS Portal — senza hardcoding nel codice.

#### Configurazione (`config/settings.py`)

```python
ARCGIS_FIELD_MAPPINGS = {
    'reports': {
        'field_name': 'arcgis_item_id',  # es. 'tipologia_appalto': '3fb39efc...'
    },
    # 'segnalazioni': { ... }  # aggiungere per nuovi servizi
}
ARCGIS_MAPPING_CACHE_TIMEOUT = 300  # secondi (default: 5 minuti)
```

Ogni chiave di primo livello è il nome dell'app Django. Ogni coppia `field_name: item_id` mappa un campo del feature layer all'item_id del CSV corrispondente su Portal.

> **Nota:** il `field_name` dell'app e il `list_name` nel CSV sono denominazioni indipendenti e non devono coincidere. La corrispondenza è stabilita esplicitamente in `ARCGIS_FIELD_MAPPINGS`.

#### Come funziona

1. Al primo accesso dell'utente, `apps/core/services/csv_mapping.py` scarica i CSV configurati dal Portal tramite l'API REST (`/sharing/rest/content/items/{id}/data`), usando il token ArcGIS già in cache.
2. Costruisce un dizionario interno `{ field_name: { code: label } }` e lo salva in cache (LocMemCache).
3. Le richieste successive leggono dalla cache — nessuna chiamata al Portal.
4. Alla scadenza del TTL, il primo accesso successivo scarica di nuovo i CSV e aggiorna la cache.

La colonna `list_name` dei CSV è ignorata a runtime; contano solo le colonne `name` (codice) e `label` (etichetta).

#### Aggiornare i mapping senza deploy

Per aggiungere un nuovo valore (es. un nuovo operatore): aggiornare il CSV su ArcGIS Portal. La webapp lo vedrà automaticamente entro `ARCGIS_MAPPING_CACHE_TIMEOUT` secondi.

Per forzare il refresh immediato senza attendere il TTL:
```python
# Django shell: uv run python manage.py shell
from django.core.cache import cache
cache.delete('arcgis_csv_mappings_reports')
```

Per aggiungere un nuovo campo al mapping: aggiungere la coppia `'field_name': 'item_id'` in `ARCGIS_FIELD_MAPPINGS['reports']` — nessuna modifica al codice applicativo.

#### Variabile d'ambiente

| Variabile | Default | Descrizione |
|---|---|---|
| `ARCGIS_MAPPING_CACHE_TIMEOUT` | `300` | Secondi di validità della cache dei mapping CSV |

#### Comportamento in caso di errore

| Scenario | Comportamento |
|---|---|
| Portal non raggiungibile / errore HTTP | Eccezione propagata → pagina di errore 500 |
| Token ArcGIS non valido o scaduto | Eccezione propagata → pagina di errore 500 |
| `item_id` non ancora configurato (placeholder) | Log di warning → fallback ai valori hardcoded in `FIELD_VALUES` |
| `field_name` non presente in `ARCGIS_FIELD_MAPPINGS` | Fallback ai valori hardcoded in `FIELD_VALUES` |
| Codice non trovato nel CSV (valore sconosciuto) | Viene mostrato il codice grezzo (es. `nuovo_valore`) |
| `ARCGIS_FIELD_MAPPINGS` vuoto o assente | Usa interamente i valori hardcoded in `FIELD_VALUES` |

## Production Deployment (Docker)

### Prerequisites

- Docker & Docker Compose installed on the VM
- `.env.prod` file present in the project root
- SSL certificates in `docker/nginx/ssl/`

### `.env.prod` required variables

```env
SECRET_KEY=<strong-random-key>
DEBUG=False
ALLOWED_HOSTS=reports.serravalle.it
CSRF_TRUSTED_ORIGINS=https://reports.serravalle.it

# Database
POSTGRES_USER=<db-user>
POSTGRES_PASSWORD=<db-password>
POSTGRES_DB=<db-name>
DATABASE_URL=postgres://<user>:<password>@db:5432/<db-name>

# Redis
REDIS_PASSWORD=<redis-password>
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0

# Azure OIDC
AZURE_TENANT_ID=<tenant-uuid>
AZURE_CLIENT_ID=<client-id>
AZURE_CLIENT_SECRET=<client-secret>

# pgAdmin
PGADMIN_DEFAULT_EMAIL=admin@serravalle.it
PGADMIN_DEFAULT_PASSWORD=<strong-password>
PGADMIN_CONFIG_SERVER_MODE=True
PGADMIN_CONFIG_SCRIPT_NAME=/pgadmin
```

### First-time deployment

```bash
# 1. Pull latest code
git pull

# 2. Build custom images (app + nginx — pgAdmin uses a pre-built image)
docker compose --env-file .env.prod -f docker-compose.prod.yml build app nginx --no-cache

# 3. Start DB and Redis first, wait for healthy
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d db redis

# 4. Run migrations
docker compose --env-file .env.prod -f docker-compose.prod.yml run --rm app \
  uv run python manage.py migrate

# 5. Create superuser
docker compose --env-file .env.prod -f docker-compose.prod.yml run --rm app \
  uv run python manage.py createsuperuser

# 6. Seed service definitions and groups
docker compose --env-file .env.prod -f docker-compose.prod.yml run --rm app \
  uv run python manage.py seed_services

# 7. Load fixtures (if migrating data from dev)
docker compose --env-file .env.prod -f docker-compose.prod.yml cp fixtures_prod.json app:/tmp/fixtures_prod.json
docker compose --env-file .env.prod -f docker-compose.prod.yml exec app \
  uv run python manage.py loaddata /tmp/fixtures_prod.json
docker compose --env-file .env.prod -f docker-compose.prod.yml exec --user root app \
  rm /tmp/fixtures_prod.json

# 8. Start full stack (app, nginx, pgAdmin, db, redis)
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d
```

> **pgAdmin first-time setup:** After the stack is up, open `https://reports.serravalle.it/pgadmin/` from within the `172.20.0.0/16` subnet. Log in with `PGADMIN_DEFAULT_EMAIL` / `PGADMIN_DEFAULT_PASSWORD`. Register a server: **Host** = `db`, **Port** = `5432`, **Database** = `POSTGRES_DB` value, **Username** = `POSTGRES_USER` value.

### Subsequent deployments

```bash
# 1. Pull latest code
git pull

# 2. Rebuild app image (always)
docker compose --env-file .env.prod -f docker-compose.prod.yml build app --no-cache

# 2b. Rebuild nginx image (only if docker/nginx/nginx.conf or Dockerfile changed)
docker compose --env-file .env.prod -f docker-compose.prod.yml build nginx --no-cache

# 3. Run migrations
docker compose --env-file .env.prod -f docker-compose.prod.yml run --rm app \
  uv run python manage.py migrate

# 4. Restart services (pgAdmin, db, redis restart only if image or config changed)
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d
```

### Verify deployment

```bash
# Check all containers healthy (app, db, redis, nginx, pgadmin)
docker compose --env-file .env.prod -f docker-compose.prod.yml ps

# Check DB connection
docker compose --env-file .env.prod -f docker-compose.prod.yml exec app \
  uv run python -c "from django.db import connection; connection.ensure_connection(); print('DB OK')"

# Check Redis connection
docker compose --env-file .env.prod -f docker-compose.prod.yml exec app \
  uv run python -c "from django.core.cache import cache; cache.set('test', 1); print('Redis OK' if cache.get('test') else 'Redis FAIL')"

# Check running user (should be reports_user)
docker compose --env-file .env.prod -f docker-compose.prod.yml exec app whoami

# Check pgAdmin is reachable (from within 172.20.0.0/16 subnet)
curl -skL -o /dev/null -w "%{http_code}" https://reports.serravalle.it/pgadmin/
# Expected: 200 (302 redirect to login page is also healthy)

# Tail logs
docker compose --env-file .env.prod -f docker-compose.prod.yml logs app -f
docker compose --env-file .env.prod -f docker-compose.prod.yml logs pgadmin -f
```

### Inspect application logs

```bash
LOG_DIR=$(sudo docker volume inspect $(docker volume ls -q | grep app-logs) --format '{{ .Mountpoint }}')
sudo tail -f $LOG_DIR/app.log
sudo tail -f $LOG_DIR/audit.log
sudo tail -f $LOG_DIR/arcgis.log
```

### Shutdown

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml down
```

---

## Useful Commands

```bash
# Run the development server
uv run python manage.py runserver

# Run Django system checks
uv run python manage.py check

# Create database migrations
uv run python manage.py makemigrations

# Apply migrations
uv run python manage.py migrate

# Create a superuser
uv run python manage.py createsuperuser

# Collect static files (for production)
uv run python manage.py collectstatic

# Seed/update service definitions and groups
uv run python manage.py seed_services

# Pip-audit for security vulnerabilities (with lockfile and pip-audit venv activatted)
pip-audit --locked .pip-audit/ -f columns --desc on -o .pip-audit/report-x.csv
# Recreate pylock.toml before run pip-audit if dependencies have changed: (with pip-audit venv activatted)
uv export --format pylock.toml --output-file .pip-audit/pylock.toml

# Bandit security linter (with bandit venv activatted)
bandit -c .bandit/bandit.yaml -f csv -o .bandit/report-x.csv -r .
```
