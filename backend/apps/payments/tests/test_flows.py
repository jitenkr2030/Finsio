"""
Tests for FinsioPaymentFlow — the getpaid-core bridge.

Tests the payment lifecycle: prepare → confirm_paid → confirm_failed.
"""

import uuid
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.core.choices import PaymentStatus
from apps.payments.flows import FinsioPaymentFlow
from apps.payments.models import Payment, PaymentEvent


@pytest.fixture
def payment(db):
    """Create a sample payment in NEW status."""
    return Payment.objects.create(
        amount=Decimal("49.99"),
        currency="USD",
        description="Test payment",
        reference="INV-TEST-001",
        customer_id="cust_test_001",
        customer_email="test@example.com",
        idempotency_key=uuid.uuid4().hex,
        status=PaymentStatus.NEW,
    )


@pytest.fixture
def flow():
    return FinsioPaymentFlow()


@pytest.mark.django_db
class TestFinsioPaymentFlow:

    def test_confirm_paid_sets_status(self, payment, flow):
        """Confirming a payment transitions it to PAID."""
        result = flow.confirm_paid(
            payment=payment,
            external_id="pi_test_123",
        )

        assert result.status == PaymentStatus.PAID
        assert result.external_id == "pi_test_123"
        assert result.paid_at is not None

    def test_confirm_paid_creates_event(self, payment, flow):
        """Confirming a payment creates an audit event."""
        flow.confirm_paid(
            payment=payment,
            external_id="pi_test_123",
            provider_event_id="evt_unique_001",
        )

        events = PaymentEvent.objects.filter(payment=payment)
        assert events.count() >= 1

        event = events.latest("created_at")
        assert event.event_type == PaymentEvent.EventType.STATUS_CHANGED
        assert event.new_status == PaymentStatus.PAID
        assert event.provider_event_id == "evt_unique_001"

    def test_confirm_paid_is_idempotent(self, payment, flow):
        """Duplicate provider_event_id is skipped."""
        flow.confirm_paid(
            payment=payment,
            external_id="pi_test_123",
            provider_event_id="evt_dedup_001",
        )
        flow.confirm_paid(
            payment=payment,
            external_id="pi_test_123",
            provider_event_id="evt_dedup_001",
        )

        events = PaymentEvent.objects.filter(
            payment=payment,
            provider_event_id="evt_dedup_001",
        )
        assert events.count() == 1

    def test_confirm_failed_sets_status(self, payment, flow):
        """Failed confirmation transitions to FAILED."""
        result = flow.confirm_failed(
            payment=payment,
            reason="Card declined",
        )

        assert result.status == PaymentStatus.FAILED
        assert result.failed_at is not None

    def test_confirm_failed_records_reason(self, payment, flow):
        """Failure reason is stored in provider_metadata."""
        flow.confirm_failed(
            payment=payment,
            reason="Insufficient funds",
        )

        payment.refresh_from_db()
        assert payment.provider_metadata.get("failure_reason") == "Insufficient funds"

    def test_cannot_prepare_terminal_payment(self, payment, flow):
        """Cannot prepare a payment that is already paid."""
        payment.status = PaymentStatus.PAID
        payment.save()

        with pytest.raises(ValueError, match="terminal state"):
            flow.prepare(payment, "stripe")
