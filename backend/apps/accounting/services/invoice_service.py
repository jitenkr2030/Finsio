"""
Invoice accounting service.

Handles the accounting side of invoice lifecycle:
  - Creating accrual-basis journal entries when an invoice is issued
  - Adjusting entries when an invoice is paid
  - Syncing both to the beancount audit trail
"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

logger = logging.getLogger(__name__)


class InvoiceAccountingService:
    """
    Manages accounting entries for invoices.

    Accrual basis:
        Invoice issued:   DR Accounts Receivable  CR Revenue
        Payment received: DR Bank/Processor       CR Accounts Receivable
    """

    @classmethod
    def record_invoice_issued(cls, invoice) -> str | None:
        """
        Create accounting entries when an invoice is issued.

        Uses the beancount generator for the audit trail.
        django-ledger journal entries are created via the
        ReconciliationService when payment is received.
        """
        from apps.accounting.beancount.sync import BeancountSyncService

        beancount_text = BeancountSyncService.sync_invoice(invoice)
        if beancount_text:
            logger.info("Recorded invoice %s in accounting", invoice.number)
        return beancount_text

    @classmethod
    def record_payment_received(cls, invoice, payment) -> str | None:
        """
        Create accounting entries when an invoice payment is received.
        """
        from apps.accounting.beancount.sync import BeancountSyncService

        beancount_text = BeancountSyncService.sync_payment(payment)
        if beancount_text:
            logger.info(
                "Recorded payment %s for invoice %s in accounting",
                payment.id, invoice.number,
            )
        return beancount_text

    @classmethod
    def calculate_revenue_by_category(
        cls,
        entity_slug: str,
        date_from: date,
        date_to: date,
    ) -> list[dict]:
        """
        Calculate revenue breakdown by line item category.
        """
        from apps.invoicing.models import InvoiceLineItem

        items = InvoiceLineItem.objects.filter(
            invoice__entity__slug=entity_slug,
            invoice__status__in=["paid", "partial"],
            invoice__paid_at__date__range=[date_from, date_to],
        )

        from django.db.models import Sum, F
        from django.db.models.functions import Coalesce

        return list(
            items.values("category").annotate(
                total_revenue=Coalesce(
                    Sum(F("quantity") * F("unit_price")),
                    Decimal("0"),
                ),
                item_count=Sum("quantity"),
            ).order_by("-total_revenue")
        )
