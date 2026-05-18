"""
Internal authentication middleware for Finsio.

Validates that requests to /internal/ routes carry the
shared bearer token. Only the Fusio gateway should reach
these endpoints — the token is never exposed to clients.
"""

import logging

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse

logger = logging.getLogger(__name__)


class InternalAuthMiddleware:
    """
    Rejects any request to /internal/ that does not carry
    a valid Bearer token matching BACKEND_INTERNAL_TOKEN.

    Exempt paths (accessible without the token):
      - /health/
      - /django-admin/
    """

    EXEMPT_PREFIXES = ["/health/", "/django-admin/", "/webhooks/"]

    def __init__(self, get_response):
        self.get_response = get_response
        self.internal_token = settings.BACKEND_INTERNAL_TOKEN

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if request.path.startswith("/internal/"):
            if not self._is_valid_token(request):
                logger.warning(
                    "Rejected unauthenticated request to %s from %s",
                    request.path,
                    request.META.get("REMOTE_ADDR", "unknown"),
                )
                return JsonResponse(
                    {
                        "error": "unauthorized",
                        "message": "Invalid or missing internal token",
                    },
                    status=401,
                )
        return self.get_response(request)

    def _is_valid_token(self, request: HttpRequest) -> bool:
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith("Bearer "):
            return False
        token = auth_header[7:]
        if not token or not self.internal_token:
            return False
        # Constant-time comparison to prevent timing attacks
        import hmac
        return hmac.compare_digest(token, self.internal_token)
