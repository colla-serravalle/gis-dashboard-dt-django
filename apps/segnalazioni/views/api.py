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
