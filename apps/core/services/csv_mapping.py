"""
CSV-based field value mapping service.

Fetches choice-list CSVs from ArcGIS Portal and builds a per-app lookup dict
{field_name: {name: label}} used by get_field_value() in each app's mappings.py.

Config (settings.py):
    ARCGIS_FIELD_MAPPINGS = {
        'reports': {
            'field_name': 'csv_item_id',
            ...
        },
    }

Each CSV must have at least the columns: name, label (list_name is ignored).
One item_id used by multiple field_names in the same app is fetched only once.
"""

import csv
import io
import logging
import threading

import requests
from django.conf import settings
from django.core.cache import cache

from apps.core.services.arcgis import get_arcgis_token

logger = logging.getLogger(__name__)

CACHE_KEY_PREFIX = 'arcgis_csv_mappings_'
_mapping_lock = threading.Lock()


def _fetch_single_csv(item_id: str, token: str) -> dict:
    """Download and parse a single CSV item from ArcGIS Portal.

    Returns {name: label}. The list_name column is ignored — the mapping
    between field_name and CSV is established in ARCGIS_FIELD_MAPPINGS.
    Raises requests.HTTPError on non-2xx response.
    """
    portal_base = settings.ARCGIS_PORTAL_BASE_URL.rstrip('/')
    url = f"{portal_base}/sharing/rest/content/items/{item_id}/data"
    headers = {'Referer': settings.ARCGIS_REFERER}

    response = requests.get(url, params={'token': token}, headers=headers, timeout=30)
    response.raise_for_status()

    # Explicit UTF-8-sig decode: handles BOM and preserves Italian accented characters.
    content = response.content.decode('utf-8-sig')

    result = {}
    reader = csv.DictReader(io.StringIO(content))
    for row in reader:
        name = row.get('name', '').strip()
        label = row.get('label', '').strip()
        if name and label:
            result[name] = label

    return result


def _build_app_mappings(app: str) -> dict:
    """Fetch all CSVs for an app. Returns {field_name: {name: label}}.

    Deduplicates item_ids: the same CSV used by multiple field_names is
    fetched only once. Raises on any network, HTTP, or token error.
    """
    field_mappings = getattr(settings, 'ARCGIS_FIELD_MAPPINGS', {})
    app_config = field_mappings.get(app, {})
    if not app_config:
        logger.debug('ARCGIS_FIELD_MAPPINGS[%s] missing or empty — skipping CSV fetch', app)
        return {}

    token = get_arcgis_token()

    # Fetch each unique item_id once.
    item_cache: dict[str, dict] = {}
    for item_id in set(app_config.values()):
        if item_id.startswith('PLACEHOLDER'):
            logger.warning(
                'item_id placeholder not replaced: %s — field will fall back to hardcoded values',
                item_id,
            )
            item_cache[item_id] = {}
            continue
        logger.info('Fetching CSV mapping from ArcGIS item: %s', item_id)
        item_cache[item_id] = _fetch_single_csv(item_id, token)

    # Assemble {field_name: {name: label}}.
    result = {}
    for field_name, item_id in app_config.items():
        result[field_name] = item_cache.get(item_id, {})

    logger.info('Loaded CSV mappings for app=%s: %d field(s)', app, len(result))
    return result


def get_csv_mappings(app: str) -> dict:
    """Return cached {field_name: {name: label}} for the given app.

    Fetches from ArcGIS Portal on first call or after TTL expiry.
    Thread-safe via double-checked locking (same pattern as ArcGISService.get_token()).
    Raises explicitly if the fetch fails — callers receive a Django 500.
    """
    cache_key = f'{CACHE_KEY_PREFIX}{app}'

    # Fast path — no lock needed if already cached.
    mappings = cache.get(cache_key)
    if mappings is not None:
        return mappings

    # Slow path — acquire lock, double-check, then fetch.
    with _mapping_lock:
        mappings = cache.get(cache_key)
        if mappings is None:
            mappings = _build_app_mappings(app)
            timeout = getattr(settings, 'ARCGIS_MAPPING_CACHE_TIMEOUT', 300)
            cache.set(cache_key, mappings, timeout=timeout)

    return mappings
