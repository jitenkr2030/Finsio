"""
Tests for the invoice accounting service.

Verifies that invoice issuance and payment are properly
recorded in the beancount audit trail.
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.test import override_settings

from apps.accounting.services.invoice_service import InvoiceAccountingService
from apps.accounting.models import BeancountSyncRecord
from apps.core.models import Entity


@pytest.fixture
def entity(db):
    return Entity.objects.create(
        name="Test Corp",
        slug="test-corp",
        beancount_entity_name="TestCorp",
        base_currency="USD",
    )


@pytest.mark.django_db
class TestInvoiceAccountingService:

    def test_record_invoice_issued(self, entity, tmp_path):
        """Issuing an invoice creates a beancount sync record."""
        from apps.invoicing.models import Invoice, InvoiceLineItem

        (tmp_path / "transactions").mkdir()

        invoice = Invoice.objects.create(
            number="INV-TESTACC-000001",
            entity=entity,
            customer_name="Test Customer",
            customer_email="test@example.com",
            currency="USD",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
        )
        InvoiceLineItem.objects.create(
            invoice=invoice,
            description="Service",
            quantity=Decimal("5"),
            unit_price=Decimal("200.00"),
        )

        with override_settings(BEANCOUNT_PATH=tmp_path):
            text = InvoiceAccountingService.record_invoice_issued(invoice)

        assert text is not None
        assert BeancountSyncRecord.objects.filter(
            object_type=BeancountSyncRecord.ObjectType.INVOICE,
            object_id=invoice.pk,
        ).exists()

    def test_calculate_revenue_by_category(self, entity):
        """Revenue calculation groups by line item category."""
        from apps.invoicing.models import Invoice, InvoiceLineItem
        from apps.core.choices import InvoiceStatus

        invoice = Invoice.objects.create(
            number="INV-REV-000001",
            entity=entity,
            customer_name="Revenue Customer",
            customer_email="rev@example.com",
            status=InvoiceStatus.PAID,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            paid_at=date.today(),
            total=Decimal("1000"),
        )
        InvoiceLineItem.objects.create(
            invoice=invoice,
            description="Consulting",
            quantity=Decimal("10"),
            unit_price=Decimal("100.00"),
            category="Services",
        )

        result = InvoiceAccountingService.calculate_revenue_by_category(
            entity_slug="test-corp",
            date_from=date.today() - timedelta(days=30),
            date_to=date.today() + timedelta(days=1),
        )

        assert len(result) >= 1
        assert result[0]["category"] == "Services"
