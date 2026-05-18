"""
Django app configuration for the Invoicing app.
"""

from django.apps import AppConfig


class InvoicingConfig(AppConfig):
    name = "apps.invoicing"
    verbose_name = "Invoicing"
    default_auto_field = "django.db.models.BigAutoField"
