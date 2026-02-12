"""Page views for reports app."""

import math
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views import View
from django.utils.decorators import method_decorator
from django.conf import settings

from apps.core.services.arcgis import query_feature_layer, get_attachments
from apps.reports.mappings import (
    get_field_label,
    get_field_value,
    process_attributes,
    process_features,
    format_date,
)


@method_decorator(login_required, name='dispatch')
class HomeView(View):
    """Home page view."""

    template_name = 'reports/home.html'

    def get(self, request):
        return render(request, self.template_name)


@method_decorator(login_required, name='dispatch')
class ReportListView(View):
    """Report list view with filtering, sorting, and pagination."""

    template_name = 'reports/report_list.html'

    def get(self, request):
        items_per_page = getattr(settings, 'ITEMS_PER_PAGE', 10)

        context = {
            'items_per_page': items_per_page,
            'labels': {
                'nome_operatore': get_field_label('nome_operatore'),
                'tratta': get_field_label('tratta'),
                'tipologia_appalto': get_field_label('tipologia_appalto'),
                'data_rilevamento': get_field_label('data_rilevamento'),
            }
        }

        return render(request, self.template_name, context)


@method_decorator(login_required, name='dispatch')
class ReportDetailView(View):
    """Report detail view."""

    template_name = 'reports/report_detail.html'

    def get(self, request):
        report_id = request.GET.get('id')

        if not report_id:
            return redirect('reports:report_list')

        # Query main record
        main = query_feature_layer(0, f"uniquerowid='{report_id}'")

        if not main.get('features'):
            return render(request, self.template_name, {
                'error': 'Record non trovato'
            })

        main_feature = main['features'][0]
        main_attrs = main_feature.get('attributes', {})

        # Query related records
        pk_pav = query_feature_layer(1, f"parentrowid='{report_id}'")
        impresa = query_feature_layer(2, f"parentrowid='{report_id}'")
        foto = query_feature_layer(3, f"parentrowid='{report_id}'")

        # Process data
        location_fields = [
            'tratta', 'carreggiata', 'pk_iniz', 'pk_fin',
            'area_intervento', 'nome_svincolo', 'corsie_svincolo',
            'nome_casello', 'nome_area_servizio'
        ]
        location_data = self._filter_processed_attributes(
            process_attributes(main_attrs, 'main'),
            location_fields
        )

        main_fields = [
            'nome_operatore', 'data_rilevamento', 'ora_rilevamento',
            'tipologia_appalto', 'presenza_dl', 'nome_dl',
            'presenza_cse', 'nome_cse', 'num_imprese', 'note'
        ]
        main_data = self._filter_processed_attributes(
            process_attributes(main_attrs, 'main'),
            main_fields
        )

        # Get coordinates
        coords = self._get_coordinates(main_feature)
        maps_url = None
        if coords['lat'] is not None and coords['lon'] is not None:
            maps_url = self._assemble_maps_url(coords['lat'], coords['lon'])
            location_data.append({
                'field': 'latitudine',
                'label': 'Latitudine',
                'value': f"{coords['lat']:.6f}",
            })
            location_data.append({
                'field': 'longitudine',
                'label': 'Longitudine',
                'value': f"{coords['lon']:.6f}",
            })

        # Process pavement data
        pk_pav_data = []
        pk_pav_fields = ['corsia', 'tipo_intervento_pav', 'pk_iniz_pav', 'pk_fin_pav']
        if pk_pav.get('features'):
            pk_pav_processed = process_features(pk_pav['features'], 'pk_pav')
            for feature in pk_pav_processed:
                filtered = self._filter_processed_attributes(feature['attributes'], pk_pav_fields)
                if filtered:
                    pk_pav_data.append(filtered)

        # Process company data
        impresa_data = []
        if impresa.get('features'):
            impresa_processed = process_features(impresa['features'], 'impresa')
            for feature in impresa_processed:
                if feature['attributes']:
                    impresa_data.append(feature['attributes'])

        # Process photos
        photos = []
        if foto.get('features'):
            for f in foto['features']:
                obj_id = f['attributes'].get('objectid')
                if obj_id:
                    attachments = get_attachments(3, obj_id)
                    if attachments.get('attachmentInfos'):
                        for att in attachments['attachmentInfos']:
                            photos.append({
                                'layer': 3,
                                'object_id': obj_id,
                                'attachment_id': att['id'],
                                'name': att.get('name', ''),
                            })

        # Get route logo
        tratta = main_attrs.get('tratta', '')
        route_logo = self._get_route_logo(tratta)

        context = {
            'report_id': report_id,
            'object_id': main_attrs.get('objectid', 'N/A'),
            'tratta': get_field_value('tratta', tratta),
            'tratta_code': tratta,
            'route_logo': route_logo,
            'maps_url': maps_url,
            'location_data': location_data,
            'main_data': main_data,
            'pk_pav_data': pk_pav_data,
            'pk_pav_headers': self._get_headers(pk_pav_fields),
            'impresa_data': impresa_data,
            'impresa_headers': self._get_impresa_headers(impresa_data),
            'photos': photos,
        }

        return render(request, self.template_name, context)

    def _filter_processed_attributes(self, processed, fields_to_include):
        """Filter processed attributes to only include specified fields."""
        return [attr for attr in processed if attr['field'] in fields_to_include]

    def _get_coordinates(self, feature):
        """Extract lat/lon from feature geometry."""
        lat = None
        lon = None
        geom = feature.get('geometry')

        if geom:
            x = geom.get('x')
            y = geom.get('y')

            if x is not None and y is not None:
                try:
                    x = float(x)
                    y = float(y)

                    if abs(x) <= 180 and abs(y) <= 90:
                        lon = x
                        lat = y
                    else:
                        # Convert Web Mercator (EPSG:3857) to WGS84
                        lon = (x / 20037508.34) * 180
                        lat = (y / 20037508.34) * 180
                        lat = 180 / math.pi * (2 * math.atan(math.exp(lat * math.pi / 180)) - math.pi / 2)
                except (ValueError, TypeError):
                    pass

        return {'lat': lat, 'lon': lon}

    def _assemble_maps_url(self, lat, lon):
        """Build Google Maps URL."""
        return f"https://www.google.com/maps/search/?api=1&query={lat:.6f},{lon:.6f}"

    def _get_route_logo(self, tratta):
        """Get route logo filename."""
        if not tratta:
            return 'default_logo.png'

        tratta_lower = tratta.lower()
        logo_map = {
            'a7_neg': 'A7-logo.png',
            'a7_pos': 'A7-logo.png',
            'a50': 'A50-logo.png',
            'a51': 'A51-logo.png',
            'a52': 'A52-logo.png',
            'a53': 'A53-logo.png',
            'a54': 'A54-logo.png',
            'sp11': 'SP11-logo.png',
            'rf': 'RF-logo.png',
        }

        return logo_map.get(tratta_lower, 'default_logo.png')

    def _get_headers(self, fields):
        """Get headers for table."""
        return [get_field_label(f) for f in fields]

    def _get_impresa_headers(self, impresa_data):
        """Get headers from first company record."""
        if impresa_data and impresa_data[0]:
            return [attr['label'] for attr in impresa_data[0]]
        return []
