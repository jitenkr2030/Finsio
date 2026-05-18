"""
Signal handlers for the Payments app.

React to payment status changes and trigger downstream
accounting entries and invoice reconciliation.
"""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.core.choices import PaymentStatus

from .models import Payment

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Payment)
def payment_status_changed(sender, instance: Payment, created: bool, **kwargs):
    """
    When a Payment is saved, check if the status changed
    and trigger appropriate downstream actions.
    """
    if created:
        logger.info("Payment created: %s (%s %s)", instance.id, instance.amount, instance.currency)
        return

    if instance.status == PaymentStatus.PAID:
        _on_payment_paid(instance)
    elif instance.status == PaymentStatus.FAILED:
        _on_payment_failed(instance)
    elif instance.status == PaymentStatus.REFUNDED:
        _on_payment_refunded(instance)


def _on_payment_paid(payment: Payment):
    """Handle a confirmed payment."""
    logger.info(
        "Payment %s confirmed paid — triggering accounting (%s %s via %s)",
        payment.id, payment.amount, payment.currency, payment.processor,
    )

    # 1. Create accounting entries in django-ledger + beancount
    try:
        from apps.accounting.services.reconciliation_service import ReconciliationService
        ReconciliationService.record_payment_received(payment)
    except Exception as e:
        logger.exception("Failed to record payment %s in accounting: %s", payment.id, e)

    # 2. Update linked invoice if present
    if payment.invoice_id:
        try:
            from apps.invoicing.services.reconcile_invoice import reconcile_invoice_payment
            reconcile_invoice_payment(payment)
        except Exception as e:
            logger.exception("Failed to reconcile payment %s with invoice: %s", payment.id, e)


def _on_payment_failed(payment: Payment):
    """Handle a failed payment."""
    logger.warning(
        "Payment %s failed (processor: %s, reason: %s)",
        payment.id,
        payment.processor,
        payment.provider_metadata.get("failure_reason", "unknown"),
    )
    # Future: send failure notification email to customer


def _on_payment_refunded(payment: Payment):
    """Handle a refunded payment."""
    logger.info(
        "Payment %s refunded (%s %s)",
        payment.id, payment.amount_refunded, payment.currency,
    )
    # Future: create refund accounting entries, notify customer
