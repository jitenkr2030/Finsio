"""
Payment models for Finsio.

Central models:
  - Payment:       unified payment record across all processors
  - PaymentEvent:  immutable audit log of every state transition
  - PaymentMethod: saved payment method tokens for returning customers

These models work alongside (not replace) django-payments and
getpaid-core. They provide a single source of truth that the
rest of Finsio queries for status, reconciliation, and reporting.
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.choices import Currency, PaymentStatus, ProcessorChoice
from apps.core.models import TimeStampedModel


class Payment(TimeStampedModel):
    """
    Unified payment record.

    Created when a client calls POST /payments/prepare.
    Status transitions:
        NEW → PREPARED → IN_PROGRESS → PAID
                                          ↘ FAILED
                                          ↘ REFUNDED
                           ↘ CANCELLED
    """

    # Core fields
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.NEW,
        db_index=True,
    )
    processor = models.CharField(
        max_length=30,
        choices=ProcessorChoice.choices,
        null=True,
        blank=True,
        db_index=True,
    )

    # Financial
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.USD)
    amount_refunded = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    # External reference at the payment provider
    external_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True,
        help_text="Payment ID at the provider (e.g. Stripe pi_xxx)",
    )
    idempotency_key = models.CharField(max_length=64, unique=True)

    # Customer
    customer_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    customer_email = models.EmailField(null=True, blank=True)

    # Descriptive
    description = models.TextField(blank=True)
    reference = models.CharField(max_length=255, blank=True, db_index=True)

    # Raw provider response
    provider_metadata = models.JSONField(default=dict, blank=True)

    # URLs
    redirect_url = models.URLField(
        null=True,
        blank=True,
        help_text="URL to redirect customer to complete payment",
    )
    callback_url = models.URLField(
        null=True,
        blank=True,
        help_text="URL to notify after payment completion",
    )

    # Link to invoice (nullable — not all payments are invoice-driven)
    invoice = models.ForeignKey(
        "invoicing.Invoice",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="payments",
    )

    # Timestamps for key transitions
    paid_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["processor", "external_id"]),
            models.Index(fields=["customer_id", "status"]),
        ]

    def __str__(self) -> str:
        return f"Payment({self.id}) [{self.status}] {self.amount} {self.currency}"

    def mark_paid(self, external_id: str, metadata: dict | None = None):
        """Transition to PAID status."""
        self.status = PaymentStatus.PAID
        self.external_id = external_id
        self.paid_at = timezone.now()
        if metadata:
            self.provider_metadata = {**self.provider_metadata, **metadata}
        self.save(update_fields=[
            "status", "external_id", "paid_at",
            "provider_metadata", "updated_at",
        ])

    def mark_failed(self, reason: str = "", metadata: dict | None = None):
        """Transition to FAILED status."""
        self.status = PaymentStatus.FAILED
        self.failed_at = timezone.now()
        if metadata:
            self.provider_metadata = {**self.provider_metadata, **metadata}
        self.provider_metadata["failure_reason"] = reason
        self.save(update_fields=[
            "status", "failed_at", "provider_metadata", "updated_at",
        ])

    def mark_refunded(self, refund_id: str, amount: float, metadata: dict | None = None):
        """Transition to REFUNDED status."""
        self.status = PaymentStatus.REFUNDED
        self.amount_refunded = amount
        if metadata:
            self.provider_metadata = {**self.provider_metadata, **metadata}
        self.provider_metadata["refund_id"] = refund_id
        self.save(update_fields=[
            "status", "amount_refunded", "provider_metadata", "updated_at",
        ])

    @property
    def is_terminal(self) -> bool:
        """True if the payment is in a final state."""
        return self.status in {
            PaymentStatus.PAID,
            PaymentStatus.FAILED,
            PaymentStatus.CANCELLED,
            PaymentStatus.REFUNDED,
        }


class PaymentEvent(TimeStampedModel):
    """
    Immutable audit log of every payment state transition
    and provider event.

    Used for:
      - Idempotent webhook processing (check provider_event_id)
      - Debugging failed payments
      - Compliance audit trail
    """

    class EventType(models.TextChoices):
        CREATED = "created", "Created"
        PREPARED = "prepared", "Prepared"
        STATUS_CHANGED = "status_changed", "Status Changed"
        PROVIDER_EVENT = "provider_event", "Provider Event"
        WEBHOOK_RECEIVED = "webhook_received", "Webhook Received"
        REFUND = "refund", "Refund"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name="events",
    )
    event_type = models.CharField(max_length=30, choices=EventType.choices)
    old_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20, blank=True)
    provider_event_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True,
        help_text="Provider event ID for idempotent processing",
    )
    data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["payment", "event_type", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"Event({self.event_type}) on {self.payment_id}"


class PaymentMethod(TimeStampedModel):
    """
    Saved payment method token for returning customers.

    Stores the provider's token (e.g. Stripe PaymentMethod ID)
    so returning customers can pay without re-entering details.
    """

    class ProviderMethod(models.TextChoices):
        STRIPE_CARD = "stripe_card", "Stripe Card"
        STRIPE_SEPA = "stripe_sepa", "Stripe SEPA Debit"
        STRIPE_ACH = "stripe_ach", "Stripe ACH Direct Debit"
        PAYPAL_BILLING = "paypal_billing", "PayPal Billing Agreement"
        BRAINTREE_CARD = "braintree_card", "Braintree Card"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer_id = models.CharField(max_length=255, db_index=True)
    provider = models.CharField(max_length=30, choices=ProviderMethod.choices)
    external_token = models.CharField(
        max_length=255,
        help_text="Provider's payment method token",
    )
    display_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Human-readable name (e.g. Visa ending 4242)",
    )
    is_default = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = [("customer_id", "provider", "external_token")]
        ordering = ["-is_default", "-created_at"]

    def __str__(self) -> str:
        return f"{self.provider}: {self.display_name or self.external_token[:12]}"
