"""
Tests for the beancount synchronization service.

Verifies that financial records are correctly exported
to .beancount files with exactly-once semantics.
"""

import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from django.test import override_settings

from apps.accounting.beancount.generator import BeancountGenerator
from apps.accounting.beancount.sync import BeancountSyncService
from apps.accounting.models import BeancountSyncRecord
from apps.core.choices import PaymentStatus
from apps.payments.models import Payment


@pytest.fixture
def tmp_beancount_path(tmp_path):
    """Create a temporary beancount directory structure."""
    (tmp_path / "transactions").mkdir()
    return tmp_path


@pytest.fixture
def generator(tmp_beancount_path):
    """BeancountGenerator using a temp directory."""
    with override_settings(BEANCOUNT_PATH=tmp_beancount_path):
        return BeancountGenerator("TestEntity")


@pytest.fixture
def paid_payment(db):
    """A paid payment for sync tests."""
    return Payment.objects.create(
        amount=Decimal("250.00"),
        currency="USD",
        description="Sync test payment",
        reference="INV-SYNC-001",
        customer_id="cust_sync_001",
        customer_email="sync@example.com",
        idempotency_key=uuid.uuid4().hex,
        status=PaymentStatus.PAID,
        processor="stripe",
        external_id="pi_sync_test",
    )


@pytest.mark.django_db
class TestBeancountGenerator:

    def test_generate_journal_entry(self, generator, tmp_beancount_path):
        """Journal entry produces valid beancount text."""
        text = generator.generate_journal_entry(
            entry_date=date(2025, 1, 15),
            description="Test transaction",
            postings=[
                {"account": "Expenses:Office", "amount": Decimal("100.00"), "currency": "USD"},
                {"account": "Assets:Bank:Operating", "amount": Decimal("-100.00"), "currency": "USD"},
            ],
        )

        assert "2025-01-15" in text
        assert "Test transaction" in text
        assert "TestEntity:Expenses:Office" in text
        assert "100.00" in text

        # Verify file was created
        file_path = tmp_beancount_path / "transactions" / "2025-01-15.beancount"
        assert file_path.exists()

    def test_generate_invoice_entry(self, generator):
        """Invoice entry debits AR and credits revenue."""
        text = generator.generate_invoice_entry(
            entry_date=date(2025, 3, 1),
            invoice_number="INV-TEST-001",
            customer_name="Test Customer",
            line_items=[
                {"description": "Consulting", "quantity": 10, "unit_price": 150, "category": "Services"},
            ],
            currency="USD",
        )

        assert "INV-TEST-001" in text
        assert "AccountsReceivable" in text
        assert "Revenue" in text
        assert "1500.00" in text

    def test_generate_payment_entry(self, generator):
        """Payment entry debits processor and credits AR."""
        text = generator.generate_payment_entry(
            payment_date=date(2025, 3, 5),
            payment_id="pay_001",
            amount=Decimal("1500.00"),
            processor="stripe",
        )

        assert "PaymentProcessors:Stripe" in text
        assert "AccountsReceivable" in text

    def test_generate_refund_entry(self, generator):
        """Refund entry debits refunds and credits processor."""
        text = generator.generate_refund_entry(
            refund_date=date(2025, 3, 10),
            payment_id="pay_001",
            amount=Decimal("500.00"),
            processor="paypal",
        )

        assert "Refunds" in text
        assert "PaymentProcessors:Paypal" in text

    def test_account_qualification(self, generator):
        """Accounts are prefixed with entity name."""
        assert generator._qualify_account("Assets:Bank:Operating") == "TestEntity:Assets:Bank:Operating"
        assert generator._qualify_account("TestEntity:Assets:Cash") == "TestEntity:Assets:Cash"

    def test_amount_formatting(self):
        """Amounts are formatted with 2 decimal places."""
        assert BeancountGenerator._format_amount(Decimal("100")) == "100.00"
        assert BeancountGenerator._format_amount(Decimal("49.9")) == "49.90"
        assert BeancountGenerator._format_amount(99.999) == "100.00"


@pytest.mark.django_db
class TestBeancountSyncService:

    def test_sync_payment_creates_record(self, paid_payment, tmp_beancount_path):
        """Syncing a payment creates a BeancountSyncRecord."""
        with override_settings(BEANCOUNT_PATH=tmp_beancount_path):
            text = BeancountSyncService.sync_payment(paid_payment)

        assert text is not None
        assert BeancountSyncRecord.objects.filter(
            object_type=BeancountSyncRecord.ObjectType.PAYMENT,
            object_id=paid_payment.pk,
        ).exists()

    def test_sync_payment_is_idempotent(self, paid_payment, tmp_beancount_path):
        """Syncing the same payment twice returns None on second call."""
        with override_settings(BEANCOUNT_PATH=tmp_beancount_path):
            first = BeancountSyncService.sync_payment(paid_payment)
            second = BeancountSyncService.sync_payment(paid_payment)

        assert first is not None
        assert second is None

    def test_get_sync_status(self, paid_payment, tmp_beancount_path):
        """get_sync_status returns True after sync."""
        assert BeancountSyncService.get_sync_status(
            BeancountSyncRecord.ObjectType.PAYMENT,
            paid_payment.pk,
        ) is False

        with override_settings(BEANCOUNT_PATH=tmp_beancount_path):
            BeancountSyncService.sync_payment(paid_payment)

        assert BeancountSyncService.get_sync_status(
            BeancountSyncRecord.ObjectType.PAYMENT,
            paid_payment.pk,
        ) is True

    def test_get_sync_stats(self, paid_payment, tmp_beancount_path):
        """get_sync_stats returns counts by type."""
        with override_settings(BEANCOUNT_PATH=tmp_beancount_path):
            BeancountSyncService.sync_payment(paid_payment)

        stats = BeancountSyncService.get_sync_stats()
        assert stats.get("payment", 0) >= 1
