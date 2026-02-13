"""PDF export view for reports."""

import io
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.views.decorators.http import require_GET
from xhtml2pdf import pisa

from apps.reports.mappings import get_field_value
from apps.reports.services.report_data import get_report_data
from apps.reports.services.image_utils import (
    fetch_attachment_as_base64,
    local_image_to_base64_uri,
)

logger = logging.getLogger(__name__)


@login_required
@require_GET
def export_pdf(request):
    """Generate and return a PDF for a report."""
    report_id = request.GET.get('rowid')
    if not report_id:
        return HttpResponse("Parametro 'rowid' mancante.", status=400)

    # Fetch all report data
    data = get_report_data(report_id)
    if data is None:
        return HttpResponse("Record non trovato.", status=404)

    raw = data['raw_attributes']

    # Company logo
    static_dir = settings.STATICFILES_DIRS[0]
    company_logo_base64 = local_image_to_base64_uri(
        str(static_dir / 'img' / 'logo-serravalle.png')
    )

    # Signature from layer 0 (first attachment only)
    signature_base64 = None
    if data['signature_attachments']:
        att = data['signature_attachments'][0]
        signature_base64 = fetch_attachment_as_base64(
            att['layer'], att['object_id'], att['attachment_id'],
            fix_orientation=False
        )

    # Photos from layer 3 — fetch in parallel
    photos_base64 = []
    if data['photos']:
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_photo = {
                executor.submit(
                    fetch_attachment_as_base64,
                    p['layer'], p['object_id'], p['attachment_id'],
                    True
                ): p
                for p in data['photos']
            }
            for future in as_completed(future_to_photo):
                photo = future_to_photo[future]
                try:
                    result = future.result()
                    if result:
                        photos_base64.append({
                            'base64': result,
                            'name': photo.get('name', ''),
                        })
                except Exception:
                    logger.exception("Error fetching photo attachment")

    # Extract formatted values for title/signature
    nome_operatore = get_field_value('nome_operatore', raw.get('nome_operatore'))
    data_rilevamento = _get_formatted_value(data['main_data'], 'data_rilevamento')

    # Build template context
    context = {
        'company_logo_base64': company_logo_base64,
        'object_id': data['object_id'],
        'globalid': raw.get('globalid', 'N/A'),
        'report_id': data['report_id'],
        'data_rilevamento': data_rilevamento,
        'nome_operatore': nome_operatore,
        'location_data': data['location_data'],
        'main_data': data['main_data'],
        'pk_pav_data': data['pk_pav_data'],
        'pk_pav_headers': data['pk_pav_headers'],
        'impresa_data': data['impresa_data'],
        'impresa_headers': data['impresa_headers'],
        'signature_base64': signature_base64,
        'photos_base64': photos_base64,
    }

    # Render HTML and generate PDF
    html_string = render_to_string('reports/report_pdf.html', context)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Verbale_{report_id}.pdf"'

    result = pisa.CreatePDF(
        io.BytesIO(html_string.encode('utf-8')),
        dest=response,
        encoding='utf-8',
    )

    if result.err:
        logger.error(f"PDF generation error for report {report_id}: {result.err}")
        return HttpResponse("Errore nella generazione del PDF.", status=500)

    return response


def _get_formatted_value(processed_data, field_name):
    """Extract a formatted value from processed attribute list by field name."""
    for attr in processed_data:
        if attr.get('field') == field_name:
            return attr.get('value', '')
    return ''
