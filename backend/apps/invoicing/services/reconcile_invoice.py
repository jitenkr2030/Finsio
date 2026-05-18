"""
Invoice reconciliation service.

When a payment is confirmed, updates the linked invoice's
paid amount, status, and handles partial payments.
"""

from __future__ import annotations

import logging
from decimal import Decimal

from apps.payments.models import Payment

from ..models import Invoice

logger = logging.getLogger(__name__)


def reconcile_invoice_payment(payment: Payment) -> None:
    """
    Reconcile a confirmed payment with its linked invoice.

    Handles:
      - Full payments: invoice → PAID
      - Partial payments: invoice → PARTIAL
      - Overpayment: invoice → PAID (excess is noted)

    Args:
        payment: A Payment instance that has been confirmed as PAID
    """
    if not payment.invoice_id:
        logger.debug("Payment %s has no linked invoice — skipping reconciliation", payment.id)
        return

    invoice = payment.invoice
    payment_amount = payment.amount

    # Calculate new paid amount
    invoice.amount_paid += payment_amount
    invoice.amount_due = invoice.total - invoice.amount_paid

    # Determine new status
    if invoice.amount_due <= Decimal("0"):
        invoice.status = "paid"
        invoice.amount_due = Decimal("0")
        if not invoice.paid_at:
            from django.utils import timezone
            invoice.paid_at = payment.paid_at or timezone.now()
        logger.info(
            "Invoice %s fully paid (%s %s, payment %s)",
            invoice.number, invoice.total, invoice.currency, payment.id,
        )
    else:
        invoice.status = "partial"
        logger.info(
            "Invoice %s partially paid: %s/%s %s (payment %s)",
            invoice.number, invoice.amount_paid, invoice.total,
            invoice.currency, payment.id,
        )

    invoice.save(update_fields=[
        "amount_paid", "amount_due", "status", "paid_at", "updated_at",
    ])

    # Sync to beancount
    try:
        from apps.accounting.beancount.sync import BeancountSyncService
        BeancountSyncService.sync_payment(payment)
    except Exception as e:
        logger.warning("Beancount sync failed for payment %s: %s", payment.id, e)
