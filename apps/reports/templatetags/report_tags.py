"""Custom template tags for reports app."""

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def route_logo(tratta, width=40):
    """
    Display the route logo image.

    Usage: {% route_logo tratta_code %}
    """
    if not tratta:
        logo_file = 'default_logo.png'
    else:
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
        logo_file = logo_map.get(tratta_lower, 'default_logo.png')

    return mark_safe(
        f'<img src="/static/img/loghi-tratte/{logo_file}" alt="{tratta} logo" width="{width}">'
    )


@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary."""
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None


@register.filter
def split(value, delimiter=','):
    """Split a string by delimiter."""
    if value:
        return [v.strip() for v in str(value).split(delimiter)]
    return []


@register.filter
def trim(value):
    """Trim whitespace from a string."""
    if value:
        return str(value).strip()
    return ''
