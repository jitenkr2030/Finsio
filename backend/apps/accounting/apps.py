"""
Django app configuration for the Accounting app.

Ensures beancount sync records and reporting services
are loaded when Django starts.
"""

from django.apps import AppConfig


class AccountingConfig(AppConfig):
    name = "apps.accounting"
    verbose_name = "Accounting"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        import apps.accounting.signals  # noqa: F401
