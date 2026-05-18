"""
Django app configuration for the Payments app.

Uses 'finsio_payments' as the app label to avoid collision
with django-payments (which uses 'payments').
"""

from django.apps import AppConfig


class PaymentsConfig(AppConfig):
    name = "apps.payments"
    label = "finsio_payments"
    verbose_name = "Finsio Payments"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        import apps.payments.signals  # noqa: F401
