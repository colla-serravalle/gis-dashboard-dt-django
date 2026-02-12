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

WSGI_APPLICATION = 'config.wsgi.application'


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
