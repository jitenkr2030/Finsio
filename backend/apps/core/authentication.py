"""
DRF authentication classes for Finsio.

InternalTokenAuthentication validates the shared bearer token
on /internal/ endpoints called by the Fusio gateway.
"""

from django.conf import settings
from django.contrib.auth.models import User
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


class InternalTokenAuthentication(BaseAuthentication):
    """
    Authenticates requests that carry the internal bearer token.

    Used on all /internal/* endpoints consumed exclusively by
    the Fusio gateway. Returns a system user for request.user.
    """

    SYSTEM_USERNAME = "finsio-system"

    def authenticate(self, request):
        auth = request.META.get("HTTP_AUTHORIZATION", "")

        if not auth.startswith("Bearer "):
            # Let other auth classes try (e.g. session auth for admin)
            return None

        token = auth[7:]

        if not token:
            return None

        import hmac
        if not hmac.compare_digest(token, settings.BACKEND_INTERNAL_TOKEN):
            raise AuthenticationFailed("Invalid internal token")

        # Return or create a system user for internal calls
        user, _ = User.objects.get_or_create(
            username=self.SYSTEM_USERNAME,
            defaults={
                "is_staff": True,
                "is_active": True,
                "is_superuser": False,
            },
        )
        return (user, "internal-token")

    def authenticate_header(self, request):
        return "Bearer"
