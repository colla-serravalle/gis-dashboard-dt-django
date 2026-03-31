"""
Django settings for GIS Dashboard DT project.

Migrated from PHP application.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import ssl
import truststore

# Capture original ssl.SSLContext BEFORE truststore replaces it
_OriginalSSLContext = ssl.SSLContext

# Use the OS certificate store for SSL verification (fixes corporate proxy/internal CA issues).
# inject_into_ssl() patches both ssl.SSLContext and urllib3.util.ssl_.SSLContext.
truststore.inject_into_ssl()

# truststore.SSLContext.__init__ never calls super().__init__(), so the inherited C
# structure is not initialized — it can't be used directly as a server SSL context.
# Werkzeug creates the dev HTTPS server context via ssl.SSLContext(PROTOCOL_TLS_SERVER).
# Fix: restore ssl.SSLContext to the original so Werkzeug gets a proper server context.
# urllib3 retains its own truststore-patched reference, so ArcGIS/outbound HTTPS
# requests still go through truststore for corporate CA verification.
ssl.SSLContext = _OriginalSSLContext

# Load environment variables
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ['SECRET_KEY']  # Crash loudly if not set — no insecure fallback

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 'yes')

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party
    'django_extensions',
    'mozilla_django_oidc',
    # Local apps
    'apps.accounts',
    'apps.authorization',
    'apps.core',
    'apps.reports',
    'apps.segnalazioni',
    'apps.audit',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'mozilla_django_oidc.middleware.SessionRefresh',
    # Service-level access control (runs after user is authenticated)
    'apps.authorization.middleware.ServiceAccessMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'config.middleware.ContentSecurityPolicyMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.authorization.context_processors.accessible_services',
            ],
        },
    },
]

ASGI_APPLICATION = 'config.asgi.application'


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'it-it'

TIME_ZONE = 'Europe/Rome'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
STATIC_ROOT = BASE_DIR / 'staticfiles'


# Default primary key field type
# https://docs.djangoproject.com/en/6.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Authentication settings
AUTHENTICATION_BACKENDS = [
    'apps.accounts.auth.AzureOIDCBackend',
    'apps.accounts.auth.SuperuserOnlyModelBackend',
]
# Redirect unauthenticated users to the unified login page
LOGIN_URL = '/auth/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# =============================================================================
# Azure AD / OIDC Configuration (mozilla-django-oidc)
# =============================================================================

AZURE_TENANT_ID = os.environ.get('AZURE_TENANT_ID')

OIDC_RP_CLIENT_ID = os.environ.get('AZURE_CLIENT_ID')
OIDC_RP_CLIENT_SECRET = os.environ.get('AZURE_CLIENT_SECRET')
OIDC_RP_SIGN_ALGO = 'RS256'
OIDC_RP_SCOPES = 'openid email profile'

OIDC_OP_JWKS_ENDPOINT = f'https://login.microsoftonline.com/{AZURE_TENANT_ID}/discovery/v2.0/keys'
OIDC_OP_AUTHORIZATION_ENDPOINT = f'https://login.microsoftonline.com/{AZURE_TENANT_ID}/oauth2/v2.0/authorize'
OIDC_OP_TOKEN_ENDPOINT = f'https://login.microsoftonline.com/{AZURE_TENANT_ID}/oauth2/v2.0/token'
OIDC_OP_USER_ENDPOINT = 'https://graph.microsoft.com/oidc/userinfo'


# Silently renew OIDC token every 15 minutes via SessionRefresh middleware
OIDC_RENEW_ID_TOKEN_EXPIRY_SECONDS = 900

# Session settings
SESSION_COOKIE_AGE = int(os.getenv('SESSION_TIMEOUT', 3600))  # 1 hour default
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_SAVE_EVERY_REQUEST = True  # Update session on every request
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Strict'


# =============================================================================
# Service Authorization Configuration
# =============================================================================

# URL namespaces (app_name) that bypass service access checks
SERVICE_AUTH_EXEMPT_APPS = [
    "authorization",
    "admin",
    "oidc",
    "accounts",
]

# URL prefixes that bypass service access checks
_ADMIN_URL = os.environ.get('DJANGO_ADMIN_URL', 'app-control-panel/')
SERVICE_AUTH_EXEMPT_URLS = [
    "/oidc/",
    f"/{_ADMIN_URL.strip('/')}/" if not _ADMIN_URL.startswith('/') else _ADMIN_URL,
    "/static/",
    "/health/",
    "/auth/",
    "/accounts/",
]

# Policy for apps without a Service record: "allow" or "deny"
SERVICE_AUTH_DEFAULT_POLICY = "deny"


# =============================================================================
# ArcGIS Configuration
# =============================================================================

ARCGIS_PORTAL_TOKEN_URL = os.getenv(
    'ARCGIS_PORTAL_TOKEN_URL',
    'https://gisserver.serravalle.it/portal/sharing/rest/generateToken'
)

ARCGIS_FEATURE_SERVICE_URL = os.getenv(
    'ARCGIS_FEATURE_SERVICE_URL',
    'https://gisserver.serravalle.it/server/rest/services/Hosted/service_bfa0d5450bcd491bb1732edc3ce173ad/FeatureServer'
)

ARCGIS_USERNAME = os.getenv('ARCGIS_USERNAME', '')
ARCGIS_PASSWORD = os.getenv('ARCGIS_PASSWORD', '')
ARCGIS_REFERER = os.getenv('ARCGIS_REFERER', 'https://reports.serravalle.it/')
ARCGIS_TOKEN_EXPIRATION_MINUTES = int(os.getenv('ARCGIS_TOKEN_EXPIRATION_MINUTES', 60))

# Base portal URL (without /sharing/rest/...) used to build content item download URLs.
ARCGIS_PORTAL_BASE_URL = os.getenv(
    'ARCGIS_PORTAL_BASE_URL',
    'https://gisserver.serravalle.it/portal'
)

# Mapping of field_name → ArcGIS Portal CSV item_id, organized by app/service.
# Structure: { 'app_name': { 'field_name': 'csv_item_id' } }
# Each CSV (published on Portal) must have the columns: list_name, name, label.
# The list_name column is ignored: the field↔CSV mapping is defined here.
# Replace placeholders with the actual ArcGIS Portal item_ids.
ARCGIS_FIELD_MAPPINGS = {
    'reports': {
        'tipologia_appalto':    '3fb39efce22042219101dde54ad19296',    # expected list_name: tipo_appalto
        'nome_operatore':       'c34cf657e62f4938b2156e8d0b4f604a',        # expected list_name: operatore_mosc (or equivalent)
        'nome_dl':              'b36a839ac3a64e3583dc456b839fe5dd',               # expected list_name: nome_dl
        'nome_cse':             '20d2b7b1ce764872b120d32dbd1d70a9',              # expected list_name: nome_cse
        'tratta':               '9bf9549a40164608a4487f1c531d8922',                # expected list_name: tratta
        'nome_impresa':         '71908fca5de947fa9a84078a4bf2de67',          # expected list_name: nome_impresa
        # 'cantierizzazione':     'PLACEHOLDER_CANTIERIZZAZIONE',      # expected list_name: cantierizzazione
        # 'presenza_dl':          'PLACEHOLDER_PRESENZA_DL',           # expected list_name: presenza_dl
        # 'presenza_cse':         'PLACEHOLDER_PRESENZA_CSE',          # expected list_name: presenza_cse
        # 'rapp_contrattuale':    'PLACEHOLDER_RAPP_CONTRATTUALE',     # expected list_name: rapp_contrattuale
        'tipo_intervento_pav':  'fba4289897c6450ea626b106de53e260',  # expected list_name: tipo_intervento_pav
        # 'carreggiata':          'PLACEHOLDER_CARREGGIATA',           # expected list_name: carreggiata
        'corsie_svincolo':      '0ad56059474d4897aeb80e09cdefde8a',       # expected list_name: corsie_svincolo
        'area_intervento':      '60605959de6e48e1985a8771b3c85d4f',       # expected list_name: area_intervento
        'nome_svincolo':        'ea5dbdc181fa4eb198c07fe8e9f0de60',         # expected list_name: nome_svincolo
        'nome_casello':         '7c08b6f383af4c3789d5e1d2a83b22c7',          # expected list_name: nome_casello
        'nome_area_servizio':   '313212d342db400480f2d77ffbc3a2a3',    # expected list_name: nome_area_servizio
        'n_squadra_pronto_int': 'b065704846cb4c43955f4b0856dfaaa1', # expected list_name: n_squadra_pronto_int
        'corsia':               '2b989f3ab6da4b209d8483caebf3b685',
    },
    # Add other services here, e.g.:
    # 'segnalazioni': {
    #     'nome_operatore': 'PLACEHOLDER_NOME_OPERATORE_DIRE',
    # },
}

# Seconds before the CSV mapping cache expires and is reloaded from Portal.
# Default: 300 s (5 min) — adjustable without redeployment via env var.
ARCGIS_MAPPING_CACHE_TIMEOUT = int(os.getenv('ARCGIS_MAPPING_CACHE_TIMEOUT', 300))


# =============================================================================
# Pagination Configuration
# =============================================================================

ITEMS_PER_PAGE = int(os.getenv('ITEMS_PER_PAGE', 10))
MAX_ITEMS_PER_PAGE = int(os.getenv('MAX_ITEMS_PER_PAGE', 100))


# =============================================================================
# Cache Configuration (for ArcGIS token caching)
# =============================================================================

_CACHE_BACKEND = os.getenv('CACHE_BACKEND', 'locmem')

if _CACHE_BACKEND == 'redis':
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/1'),
        }
    }
elif _CACHE_BACKEND == 'file':
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
            'LOCATION': os.getenv('FILE_CACHE_DIR', '/tmp/django_cache'),
        }
    }
else:
    # Default: LocMemCache — fine for development, NOT suitable for multi-instance production
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
        }
    }


# =============================================================================
# Security Settings
# =============================================================================

# Rate limiting for login attempts
MAX_LOGIN_ATTEMPTS = int(os.getenv('MAX_LOGIN_ATTEMPTS', 5))
LOCKOUT_DURATION = int(os.getenv('LOCKOUT_DURATION', 900))  # 15 minutes

# Trusted reverse proxy IPs for X-Forwarded-For extraction (space-separated in env)
LOGIN_TRUSTED_PROXIES = [
    ip.strip()
    for ip in os.getenv('LOGIN_TRUSTED_PROXIES', '').split()
    if ip.strip()
]

# Production security headers — only active when DEBUG=False
if not DEBUG:
    # SSL redirect is handled by the reverse proxy (IIS/nginx), not Django.
    # Setting this to True would cause an infinite redirect loop because the
    # proxy terminates TLS and forwards plain HTTP internally.
    SECURE_SSL_REDIRECT = False
    SECURE_HSTS_SECONDS = 31536000          # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
    SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'

# Content Security Policy — applied by config.middleware.ContentSecurityPolicyMiddleware
CSP_POLICY = {
    "default-src": ["'self'"],
    "script-src": ["'self'"],
    "style-src": ["'self'", "cdnjs.cloudflare.com"],
    "font-src": ["'self'", "cdnjs.cloudflare.com"],
    "img-src": ["'self'", "data:", "https:"],
    "connect-src": ["'self'"],
    "frame-ancestors": ["'none'"],
}

# =============================================================================
# Logging Configuration
# =============================================================================

# Log level from environment (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()

# Custom handler class for gzip compression
import gzip
import shutil
import logging.handlers


class CompressedRotatingFileHandler(logging.handlers.RotatingFileHandler):
    """RotatingFileHandler that compresses rotated logs with gzip."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rotator = self._gzip_rotator

    @staticmethod
    def _gzip_rotator(source, dest):
        """Compress the rotated log file."""
        with open(source, 'rb') as f_in:
            with gzip.open(f'{dest}.gz', 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        os.remove(source)


class WindowsSafeTimedRotatingFileHandler(logging.handlers.TimedRotatingFileHandler):
    """
    TimedRotatingFileHandler that uses copy+truncate on Windows.

    The default implementation calls os.rename(), which Windows refuses when
    any process holds an open handle to the file (WinError 32). Copy+truncate
    preserves the original inode so all existing handles stay valid.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if sys.platform == "win32":
            self.rotator = self._copy_truncate_rotator

    @staticmethod
    def _copy_truncate_rotator(source: str, dest: str) -> None:
        shutil.copy2(source, dest)
        open(source, "w").close()  # noqa: WPS515  # truncate in-place


class SuppressBrowserGenerated404Filter(logging.Filter):
    """
    Logging filter to suppress 404 warnings for known browser-generated requests.

    Filters out harmless 404s from paths like:
    - /.well-known/* (Chrome DevTools, security.txt, etc.)
    - /favicon.ico (browser automatic request)
    - /robots.txt (search engine crawlers)
    - /apple-touch-icon*.png (iOS Safari)

    Only affects WARNING-level 404 logs from django.request logger.
    Legitimate 404s (broken links with referrers) are still logged.
    """

    # Paths to suppress - easily extensible
    IGNORED_PATHS = [
        '/.well-known/',          # Catch all .well-known requests (RFC 8615)
        '/favicon.ico',
        '/robots.txt',
        '/apple-touch-icon',      # Matches apple-touch-icon.png, apple-touch-icon-precomposed.png, etc.
        '/browserconfig.xml',     # Windows/IE tiles
        '/site.webmanifest',      # PWA manifest
    ]

    def filter(self, record):
        """
        Return False to suppress the log record, True to allow it.

        Args:
            record: LogRecord instance from django.request logger

        Returns:
            bool: False if this is a browser-generated 404 to suppress, True otherwise
        """
        # Only filter 404s (status_code 404 warnings)
        if not hasattr(record, 'status_code') or record.status_code != 404: # type: ignore
            return True

        # Check if request path matches any ignored patterns
        if hasattr(record, 'request'):
            path = record.request.path # type: ignore

            for ignored_path in self.IGNORED_PATHS:
                if path.startswith(ignored_path):
                    return False  # Suppress this log

        return True  # Allow all other logs


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {name} {message}',
            'style': '{',
        },
        'audit_json': {
            '()': 'apps.audit.formatters.NIS2JsonFormatter',
        },
        'app_json': {
            '()': 'apps.audit.formatters.AppJsonFormatter',
        },
    },
    'filters': {
        # Suppress browser-generated 404 warnings (favicon, .well-known, etc.)
        'suppress_browser_404s': {
            '()': 'config.settings.SuppressBrowserGenerated404Filter',
        },
    },
    'handlers': {
        'file': {
            'level': LOG_LEVEL,
            'class': 'config.settings.CompressedRotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
            'filters': ['suppress_browser_404s'],
        },
        'app_file': {
            'level': LOG_LEVEL,
            'class': 'config.settings.CompressedRotatingFileHandler',  # reuse existing class
            'filename': BASE_DIR / 'logs' / 'app.log',
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 5,
            'encoding': 'utf-8',
            'formatter': 'app_json',
        },
        'console': {
            'level': LOG_LEVEL,
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
            'filters': ['suppress_browser_404s'],
        },
        'audit_file': {
            'level': 'INFO',
            'class': 'config.settings.WindowsSafeTimedRotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'audit.log',
            'when': 'midnight',
            'interval': 1,
            'backupCount': 365,
            'encoding': 'utf-8',
            'formatter': 'audit_json',
        },
    },
    'loggers': {
        # Explicitly configure django.request logger for clarity
        'django.request': {
            'handlers': ['console', 'file'],
            'level': 'WARNING',  # Keep at WARNING to catch 404s and 500s
            'propagate': False,
        },
        'apps': {
            'handlers': ['app_file'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'audit': {
            'handlers': ['audit_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': LOG_LEVEL,
    },
}
