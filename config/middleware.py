"""Project-level Django middleware."""

from django.conf import settings


class ContentSecurityPolicyMiddleware:
    """Attach a Content-Security-Policy header to every response.

    The policy is assembled from the CSP_POLICY dict in settings.
    Each key is a CSP directive name; the value is a list of source strings.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        policy = getattr(settings, 'CSP_POLICY', {})
        self._header_value = '; '.join(
            f"{directive} {' '.join(sources)}"
            for directive, sources in policy.items()
        )

    def __call__(self, request):
        response = self.get_response(request)
        if self._header_value:
            response['Content-Security-Policy'] = self._header_value
        return response
