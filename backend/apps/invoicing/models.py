"""
Invoice models for Finsio.

Manages the full invoice lifecycle:
  DRAFT → PENDING → PARTIAL → PAID
                       ↘ OVERDUE
                       ↘ CANCELLED

Each invoice is linked to an Entity and generates
accounting entries in both django-ledger and beancount.
"""

import uuid

from django.db import models
from django.utils import timezone

from apps.core.choices import Currency, InvoiceStatus
from apps.core.models import TimeStampedModel


class Invoice(TimeStampedModel):
    """
    Invoice that generates accounting entries and optionally
    triggers payment collection via the unified payment layer.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    number = models.CharField(max_length=50, unique=True)
    status = models.CharField(
        max_length=20,
        choices=InvoiceStatus.choices,
        default=InvoiceStatus.DRAFT,
        db_index=True,
    )

    # Entity (business owner)
    entity = models.ForeignKey(
        "core.Entity",
        on_delete=models.CASCADE,
        related_name="invoices",
    )

    # Customer
    customer_name = models.CharField(max_length=255)
    customer_email = models.EmailField()
    customer_id = models.CharField(max_length=255, blank=True, db_index=True)

    # Financials
    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.USD)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    amount_due = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    # Dates
    issue_date = models.DateField(default=timezone.now)
    due_date = models.DateField()
    paid_at = models.DateTimeField(null=True, blank=True)

    # Payment link
    payment_url = models.URLField(null=True, blank=True)
    preferred_processor = models.CharField(max_length=30, blank=True)

    # Notes
    notes = models.TextField(blank=True)

    # django-ledger reference
    ledger_je_id = models.UUIDField(
        null=True, blank=True,
        help_text="Journal entry ID in django-ledger",
    )

    class Meta:
        ordering = ["-issue_date", "-created_at"]
        indexes = [
            models.Index(fields=["entity", "status"]),
            models.Index(fields=["customer_id", "status"]),
            models.Index(fields=["due_date", "status"]),
        ]

    def __str__(self) -> str:
        return f"Invoice {self.number} [{self.status}] {self.total} {self.currency}"

    def recalculate(self):
        """Recalculate totals from line items."""
        items = self.line_items.all()
        self.subtotal = sum(item.line_total for item in items)
        self.tax_amount = sum(item.tax_amount for item in items)
        self.total = self.subtotal + self.tax_amount
        self.amount_due = self.total - self.amount_paid
        self.save(update_fields=[
            "subtotal", "tax_amount", "total", "amount_due", "updated_at",
        ])

    def mark_paid(self):
        """Mark the invoice as fully paid."""
        self.status = InvoiceStatus.PAID
        self.paid_at = timezone.now()
        self.amount_paid = self.total
        self.amount_due = 0
        self.save(update_fields=[
            "status", "paid_at", "amount_paid", "amount_due", "updated_at",
        ])

    def mark_overdue(self):
        """Mark the invoice as overdue."""
        if self.status in [InvoiceStatus.PENDING, InvoiceStatus.PARTIAL]:
            self.status = InvoiceStatus.OVERDUE
            self.save(update_fields=["status", "updated_at"])


class InvoiceLineItem(TimeStampedModel):
    """
    Individual line item on an invoice.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="line_items",
    )
    description = models.CharField(max_length=500)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=14, decimal_places=2)
    tax_rate = models.DecimalField(
        max_digits=5, decimal_places=4, default=0,
        help_text="Tax rate as decimal (e.g. 0.08 for 8%)",
    )
    category = models.CharField(
        max_length=100, blank=True, default="General",
        help_text="Revenue category for accounting (e.g. Services, Products)",
    )

    @property
    def line_total(self) -> models.DecimalField:
        """Quantity × unit price."""
        return self.quantity * self.unit_price

    @property
    def tax_amount(self) -> models.DecimalField:
        """Tax on this line."""
        return self.line_total * self.tax_rate

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.description} ({self.quantity} × {self.unit_price})"
