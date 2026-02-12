"""API views for reports app."""

import logging
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET

from apps.core.services.arcgis import query_feature_layer, get_attachments, get_arcgis_service
from apps.reports.mappings import get_field_value, format_date

logger = logging.getLogger(__name__)


def normalize_filter(value):
    """
    Normalize a filter value to a list.

    Accepts: array, single string, or comma-separated string.
    Returns: list of trimmed values.
    """
    if value is None:
        return []

    if isinstance(value, list):
        return [v.strip() for v in value if v and v.strip()]

    if isinstance(value, str):
        if ',' in value:
            return [v.strip() for v in value.split(',') if v.strip()]
        value = value.strip()
        return [value] if value else []

    return []


def apply_filters(attributes, filters):
    """
    Apply filters to a record.

    Returns True if the record passes all filters.
    """
    # Filter by operator
    if filters.get('nome_operatore'):
        if attributes.get('nome_operatore') not in filters['nome_operatore']:
            return False

    # Filter by route
    if filters.get('tratta'):
        if attributes.get('tratta') not in filters['tratta']:
            return False

    # Filter by contract type
    if filters.get('tipologia_appalto'):
        if attributes.get('tipologia_appalto') not in filters['tipologia_appalto']:
            return False

    # Filter by date range
    if filters.get('date_from') or filters.get('date_to'):
        record_timestamp = attributes.get('data_rilevamento')

        if not record_timestamp:
            return False

        try:
            timestamp = float(record_timestamp)
            # Convert milliseconds to seconds if needed
            if timestamp > 9999999999:
                timestamp = timestamp / 1000

            from datetime import datetime
            record_date = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')

            if filters.get('date_from') and record_date < filters['date_from']:
                return False

            if filters.get('date_to') and record_date > filters['date_to']:
                return False

        except (ValueError, TypeError):
            return False

    return True


def sort_records(records, sort_by, sort_order):
    """Sort records by a field."""
    if not records:
        return records

    reverse = sort_order == 'desc'

    def get_sort_key(record):
        value = record.get(sort_by, '')

        # Special handling for dates
        if sort_by == 'data_rilevamento':
            try:
                ts = float(value)
                if ts > 9999999999:
                    ts = ts / 1000
                return ts
            except (ValueError, TypeError):
                return 0

        # For strings, use case-insensitive comparison
        if isinstance(value, str):
            return value.lower()

        return value or ''

    return sorted(records, key=get_sort_key, reverse=reverse)


@login_required
@require_GET
def get_data(request):
    """
    Get paginated report data with filtering and sorting.

    Query params:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 10)
        - sort_by: Field to sort by (default: data_rilevamento)
        - sort_order: asc or desc (default: desc)
        - nome_operatore: Filter by operator (supports multiple values)
        - tratta: Filter by route (supports multiple values)
        - tipologia_appalto: Filter by contract type (supports multiple values)
        - date_from: Filter by start date (YYYY-MM-DD)
        - date_to: Filter by end date (YYYY-MM-DD)
    """
    try:
        # Parse pagination params
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 10))
        offset = (page - 1) * per_page

        # Parse sorting params
        sort_by = request.GET.get('sort_by', 'data_rilevamento')
        sort_order = request.GET.get('sort_order', 'desc').lower()
        if sort_order not in ('asc', 'desc'):
            sort_order = 'desc'

        # Parse filters
        filters = {
            'nome_operatore': normalize_filter(request.GET.getlist('nome_operatore') or request.GET.get('nome_operatore')),
            'tratta': normalize_filter(request.GET.getlist('tratta') or request.GET.get('tratta')),
            'tipologia_appalto': normalize_filter(request.GET.getlist('tipologia_appalto') or request.GET.get('tipologia_appalto')),
            'date_from': request.GET.get('date_from', '').strip(),
            'date_to': request.GET.get('date_to', '').strip(),
        }

        # Query feature layer
        result = query_feature_layer(0)

        if 'error' in result:
            return JsonResponse({'error': result['error']}, status=500)

        features = result.get('features', [])

        # Process and filter records
        records = []
        for feature in features:
            attrs = feature.get('attributes', {})

            # Apply filters
            if not apply_filters(attrs, filters):
                continue

            # Build record with mapped values
            record = {
                'uniquerowid': attrs.get('uniquerowid', ''),
                'nome_operatore': get_field_value('nome_operatore', attrs.get('nome_operatore', '')),
                'tratta': get_field_value('tratta', attrs.get('tratta', '')),
                'tipologia_appalto': get_field_value('tipologia_appalto', attrs.get('tipologia_appalto', '')),
                'data_rilevamento': attrs.get('data_rilevamento', ''),  # Keep original for sorting
            }
            records.append(record)

        # Sort records
        records = sort_records(records, sort_by, sort_order)

        # Calculate total
        total = len(records)

        # Apply pagination
        paginated_records = records[offset:offset + per_page]

        # Format dates for display
        for record in paginated_records:
            if record['data_rilevamento']:
                record['data_rilevamento'] = format_date(record['data_rilevamento'])

        return JsonResponse({
            'data': paginated_records,
            'total': total,
            'sort_by': sort_by,
            'sort_order': sort_order,
        })

    except Exception as e:
        logger.exception("Error in get_data")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_GET
def get_filter_options(request):
    """
    Get available filter options for dropdowns.

    Returns unique values for each filterable field.
    """
    try:
        result = query_feature_layer(0)

        if 'error' in result:
            return JsonResponse({'error': result['error']}, status=500)

        features = result.get('features', [])

        unique_values = {
            'nome_operatore': set(),
            'tratta': set(),
            'tipologia_appalto': set(),
            'data_rilevamento': [],
        }

        # Extract unique values
        for feature in features:
            attrs = feature.get('attributes', {})

            if attrs.get('nome_operatore'):
                unique_values['nome_operatore'].add(attrs['nome_operatore'])

            if attrs.get('tratta'):
                unique_values['tratta'].add(attrs['tratta'])

            if attrs.get('tipologia_appalto'):
                unique_values['tipologia_appalto'].add(attrs['tipologia_appalto'])

            if attrs.get('data_rilevamento'):
                unique_values['data_rilevamento'].append(attrs['data_rilevamento'])

        # Build filter options
        filter_options = {}

        for field in ['nome_operatore', 'tratta', 'tipologia_appalto']:
            values = sorted(unique_values[field])
            filter_options[field] = [
                {'value': v, 'label': get_field_value(field, v)}
                for v in values
            ]

        # Process date range
        if unique_values['data_rilevamento']:
            converted_dates = []
            for ts in unique_values['data_rilevamento']:
                try:
                    timestamp = float(ts)
                    if timestamp > 9999999999:
                        timestamp = timestamp / 1000
                    converted_dates.append(timestamp)
                except (ValueError, TypeError):
                    pass

            if converted_dates:
                from datetime import datetime
                min_date = datetime.fromtimestamp(min(converted_dates)).strftime('%Y-%m-%d')
                max_date = datetime.fromtimestamp(max(converted_dates)).strftime('%Y-%m-%d')

                filter_options['date_range'] = {
                    'min': min_date,
                    'max': max_date,
                }

        return JsonResponse(filter_options)

    except Exception as e:
        logger.exception("Error in get_filter_options")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_GET
def image_proxy(request, layer, object_id, attachment_id):
    """
    Proxy for ArcGIS attachment images.

    This endpoint fetches images from ArcGIS using the authenticated token
    and returns them to the client.
    """
    try:
        layer = int(layer)
        object_id = int(object_id)
        attachment_id = int(attachment_id)

        service = get_arcgis_service()
        content, content_type = service.get_attachment_content(layer, object_id, attachment_id)

        if content is not None:
            return HttpResponse(content, content_type=content_type)
        else:
            return HttpResponse("Errore nel recupero dell'allegato.", status=500)

    except ValueError:
        return HttpResponse("Parametri non validi.", status=400)
    except Exception as e:
        logger.exception("Error in image_proxy")
        return HttpResponse(f"Errore: {str(e)}", status=500)
