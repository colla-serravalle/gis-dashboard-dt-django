"""
URL configuration for GIS Dashboard DT project.
"""

import os
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from apps.core.views import HealthView

urlpatterns = [
    path('health/', HealthView.as_view(), name='health'),
    path(os.environ.get('DJANGO_ADMIN_URL', 'app-control-panel/'), admin.site.urls),
    path('oidc/', include('mozilla_django_oidc.urls')),
    # Redirect legacy login URL to unified login page
    path('accounts/login/', RedirectView.as_view(url='/auth/login/', permanent=False)),
    path('auth/', include('apps.accounts.urls')),
    path('api/', include('apps.reports.api_urls')),
    path('', include('apps.core.urls')),
    path('', include('apps.reports.urls')),
    path('', include('apps.segnalazioni.urls')),
    path('segnalazioni/api/', include('apps.segnalazioni.api_urls')),
    path('', include('apps.profiles.urls')),
]

# Serve static files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
