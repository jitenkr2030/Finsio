"""
URL routes for payment provider webhooks (under /webhooks/).

These are public-facing endpoints verified by provider
signatures, not by our internal auth middleware.
"""

from django.urls import path

from . import webhooks

urlpatterns = [
    path(
        "payments/<str:provider>",
        webhooks.payment_webhook,
        name="payment-webhook",
    ),
]
