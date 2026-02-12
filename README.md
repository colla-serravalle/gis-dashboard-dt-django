# GIS Dashboard DT

Internal dashboard for managing and viewing field inspection reports, built with Django. Connects to ArcGIS Enterprise to query feature layers, display report data with filtering/pagination, and proxy attachment images.

Migrated from a PHP application originally hosted on altervista.org.

## Tech Stack

- **Python** 3.13+
- **Django** 6.0.2
- **ArcGIS Enterprise** REST API (feature layers, tokens, attachments)
- **SQLite** (local auth/session storage)
- **uv** (package manager)

## Project Structure

```
gis-dashboard-dt-parent/
├── config/                # Django project configuration
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── accounts/          # Authentication (login/logout)
│   ├── core/              # Shared services
│   │   └── services/
│   │       └── arcgis.py  # ArcGIS REST API client with token caching
│   └── reports/           # Main application
│       ├── mappings.py    # Field labels and coded value mappings
│       ├── views/
│       │   ├── pages.py   # Page views (home, list, detail)
│       │   └── api.py     # JSON API endpoints
│       ├── urls.py        # Page URL routes
│       └── api_urls.py    # API URL routes
├── templates/             # Django HTML templates
├── static/                # CSS, JS, images
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

6. Start the development server:
   ```bash
   uv run python manage.py runserver
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
| `/auth/login/` | Login page |
| `/auth/logout/` | Logout |
| `/admin/` | Django admin panel |

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
| `ARCGIS_PORTAL_URL` | No | Token generation endpoint |
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

### Field Mappings

`apps/reports/mappings.py` contains coded value domain mappings ported from the original PHP application. The `get_field_value()` function translates ArcGIS coded values into human-readable labels.

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
```
