# GIS Dashboard DT

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
| `/reports/pdf/?rowid=<uniquerowid>` | Export report as PDF |
| `/profiles/` | User profile page (login required) |
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

### PDF Export

The `apps/reports/views/pdf.py` module handles report PDF generation using xhtml2pdf:

- **Template-based rendering** - Uses Django templates for consistent PDF layout
- **Embedded images** - Converts ArcGIS attachments and static assets to base64-encoded data URIs
- **EXIF orientation** - Automatically corrects photo orientation using Pillow's EXIF processing
- **Parallel fetching** - Uses ThreadPoolExecutor to fetch multiple photos concurrently
- **Branding** - Includes company logo, operator signature, and formatted report data

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
