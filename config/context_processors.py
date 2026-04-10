"""Custom template context processors."""

from config.strings import UI_STRINGS


def csp_nonce(request):
    """Expose the per-request CSP nonce to all templates."""
    return {'csp_nonce': getattr(request, 'csp_nonce', '')}


def ui_strings(request):
    """Expose UI string definitions to all templates."""
    return {"ui_strings": UI_STRINGS}
