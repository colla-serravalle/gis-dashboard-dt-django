"""
Django settings for GIS Dashboard DT project.

Migrated from PHP application.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import truststore

# Use the OS certificate store for SSL verification (fixes corporate proxy/internal CA issues)
truststore.inject_into_ssl()

# Load environment variables
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-change-this-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 'yes')

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Local apps
    'apps.accounts',
    'apps.core',
    'apps.reports',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
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
LOGIN_URL = '/auth/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/auth/login/'

# Session settings
SESSION_COOKIE_AGE = int(os.getenv('SESSION_TIMEOUT', 3600))  # 1 hour default
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_SAVE_EVERY_REQUEST = True  # Update session on every request


# =============================================================================
# ArcGIS Configuration
# =============================================================================

ARCGIS_PORTAL_URL = os.getenv(
    'ARCGIS_PORTAL_URL',
    'https://gisserver.serravalle.it/portal/sharing/rest/generateToken'
)

ARCGIS_FEATURE_SERVICE_URL = os.getenv(
    'ARCGIS_FEATURE_SERVICE_URL',
    'https://gisserver.serravalle.it/server/rest/services/Hosted/service_bfa0d5450bcd491bb1732edc3ce173ad/FeatureServer'
)

ARCGIS_USERNAME = os.getenv('ARCGIS_USERNAME', '')
ARCGIS_PASSWORD = os.getenv('ARCGIS_PASSWORD', '')
ARCGIS_REFERER = os.getenv('ARCGIS_REFERER', 'https://dtserravalle.altervista.org/')
ARCGIS_TOKEN_EXPIRATION_MINUTES = int(os.getenv('ARCGIS_TOKEN_EXPIRATION_MINUTES', 60))


# =============================================================================
# Pagination Configuration
# =============================================================================

ITEMS_PER_PAGE = int(os.getenv('ITEMS_PER_PAGE', 10))
MAX_ITEMS_PER_PAGE = int(os.getenv('MAX_ITEMS_PER_PAGE', 100))


# =============================================================================
# Cache Configuration (for ArcGIS token caching)
# =============================================================================

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
        if not hasattr(record, 'status_code') or record.status_code != 404:
            return True

        # Check if request path matches any ignored patterns
        if hasattr(record, 'request'):
            path = record.request.path

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
        'arcgis_file': {
            'level': 'DEBUG',
            'class': 'config.settings.CompressedRotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'arcgis.log',
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'console': {
            'level': LOG_LEVEL,
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
            'filters': ['suppress_browser_404s'],
        },
    },
    'loggers': {
        # Explicitly configure django.request logger for clarity
        'django.request': {
            'handlers': ['console', 'file'],
            'level': 'WARNING',  # Keep at WARNING to catch 404s and 500s
            'propagate': False,
        },
        'apps.core.services.arcgis': {
            'handlers': ['arcgis_file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': LOG_LEVEL,
    },
}
