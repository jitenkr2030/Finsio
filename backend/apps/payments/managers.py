"""
Custom model managers for the Payments app.

Provides filtered querysets for common payment lookups
and aggregation helpers for reporting.
"""

from django.db import models
from django.utils import timezone

from apps.core.choices import PaymentStatus


class PaymentQuerySet(models.QuerySet):
    """Custom queryset methods for Payment."""

    def pending(self):
        """Payments that are new or in progress."""
        return self.filter(status__in=[
            PaymentStatus.NEW,
            PaymentStatus.PREPARED,
            PaymentStatus.IN_PROGRESS,
        ])

    def completed(self):
        """Successfully paid payments."""
        return self.filter(status=PaymentStatus.PAID)

    def failed(self):
        """Failed payments."""
        return self.filter(status=PaymentStatus.FAILED)

    def refunded(self):
        """Refunded payments."""
        return self.filter(status=PaymentStatus.REFUNDED)

    def for_customer(self, customer_id: str):
        """All payments for a specific customer."""
        return self.filter(customer_id=customer_id)

    def for_processor(self, processor: str):
        """All payments processed by a specific provider."""
        return self.filter(processor=processor)

    def in_period(self, start, end):
        """Payments created within a date range."""
        return self.filter(created_at__range=[start, end])

    def paid_in_period(self, start, end):
        """Payments that were confirmed paid within a date range."""
        return self.filter(
            status=PaymentStatus.PAID,
            paid_at__range=[start, end],
        )

    def total_revenue(self, start=None, end=None):
        """Sum of paid amounts, optionally filtered by date range."""
        qs = self.completed()
        if start and end:
            qs = qs.paid_in_period(start, end)
        from django.db.models import Sum
        return qs.aggregate(total=Sum("amount"))["total"] or 0

    def revenue_by_processor(self, start=None, end=None):
        """Revenue grouped by payment processor."""
        qs = self.completed()
        if start and end:
            qs = qs.paid_in_period(start, end)
        from django.db.models import Sum
        return qs.values("processor").annotate(
            total=Sum("amount"),
            count=models.Count("id"),
        ).order_by("-total")


class PaymentManager(models.Manager):
    """Custom manager for Payment model."""

    def get_queryset(self):
        return PaymentQuerySet(self.model, using=self._db)

    def pending(self):
        return self.get_queryset().pending()

    def completed(self):
        return self.get_queryset().completed()

    def for_customer(self, customer_id: str):
        return self.get_queryset().for_customer(customer_id)

    def total_revenue(self, start=None, end=None):
        return self.get_queryset().total_revenue(start, end)
