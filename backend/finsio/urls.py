"""
Root URL configuration for Finsio.

Routes:
  /admin/          — Django admin (redirects to /django-admin/)
  /django-admin/   — Django admin (canonical)
  /api/v1/         — Public API v1 (same as /internal/)
  /internal/       — API consumed by Fusio gateway
  /webhooks/       — Payment provider webhook receivers (public)
  /health/         — Health check (public)
"""

from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import include, path


def admin_redirect(request):
    return HttpResponseRedirect("/django-admin/")


urlpatterns = [
    # Django admin
    path("django-admin/", admin.site.urls),
    path("admin/", admin_redirect),

    # Internal API endpoints (consumed by Fusio gateway only)
    path("internal/", include("apps.core.api_urls")),

    # Public API v1 (same endpoints, different auth)
    path("api/v1/", include("apps.core.api_urls")),

    # Webhook endpoints (public, provider-verified signatures)
    path("webhooks/", include("apps.payments.api.webhook_urls")),

    # Health check
    path("health/", include("apps.core.health_urls")),
]
