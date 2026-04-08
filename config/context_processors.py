"""Custom template context processors."""


def csp_nonce(request):
    """Expose the per-request CSP nonce to all templates."""
    return {'csp_nonce': getattr(request, 'csp_nonce', '')}
