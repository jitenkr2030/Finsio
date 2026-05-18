"""
Custom managers and querysets for the Invoicing app.
"""

from django.db import models
from django.utils import timezone

from apps.core.choices import InvoiceStatus


class InvoiceQuerySet(models.QuerySet):
    """Custom queryset methods for Invoice."""

    def pending(self):
        return self.filter(status=InvoiceStatus.PENDING)

    def paid(self):
        return self.filter(status=InvoiceStatus.PAID)

    def overdue(self):
        return self.filter(
            status__in=[InvoiceStatus.PENDING, InvoiceStatus.PARTIAL],
            due_date__lt=timezone.now().date(),
        )

    def for_entity(self, entity_slug: str):
        return self.filter(entity__slug=entity_slug)

    def for_customer(self, customer_id: str):
        return self.filter(customer_id=customer_id)

    def in_period(self, start, end):
        return self.filter(issue_date__range=[start, end])


class InvoiceManager(models.Manager):
    def get_queryset(self):
        return InvoiceQuerySet(self.model, using=self._db)

    def pending(self):
        return self.get_queryset().pending()

    def overdue(self):
        return self.get_queryset().overdue()

    def for_entity(self, entity_slug: str):
        return self.get_queryset().for_entity(entity_slug)
