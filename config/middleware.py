"""Project-level Django middleware."""

import secrets
from django.conf import settings


_NONCE_SENTINEL = "'nonce'"


class ContentSecurityPolicyMiddleware:
    """Attach a Content-Security-Policy header with a per-request nonce.

    The CSP_POLICY dict may include the sentinel string "'nonce'" in any
    directive's source list. It is replaced with "'nonce-<random>'" for
    every request, and the nonce value is stored on request.csp_nonce so
    templates can emit it as the nonce= attribute on <script> tags.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self._policy = getattr(settings, 'CSP_POLICY', {})

    def _build_header(self, nonce):
        parts = []
        for directive, sources in self._policy.items():
            resolved = [
                f"'nonce-{nonce}'" if s == _NONCE_SENTINEL else s
                for s in sources
            ]
            parts.append(f"{directive} {' '.join(resolved)}")
        return '; '.join(parts)

    def __call__(self, request):
        nonce = secrets.token_urlsafe(16)
        request.csp_nonce = nonce
        response = self.get_response(request)
        header = self._build_header(nonce)
        if header:
            response['Content-Security-Policy'] = header
        return response
