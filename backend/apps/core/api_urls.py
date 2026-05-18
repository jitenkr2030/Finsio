"""
Internal API URL configuration.

Routes /internal/* requests to the appropriate app URLs.
"""

from django.urls import include, path

urlpatterns = [
    path("payments/", include("apps.payments.api.urls")),
    path("accounting/", include("apps.accounting.api.urls")),
    path("invoicing/", include("apps.invoicing.api.urls")),
    path("entities/", include("apps.core.entity_urls")),
]
