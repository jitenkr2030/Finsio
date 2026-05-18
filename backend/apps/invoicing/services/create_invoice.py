"""
Invoice creation service for Finsio.

Handles the full invoice creation workflow:
  1. Generate a unique invoice number
  2. Create line items
  3. Calculate totals
  4. Post accounting entries (beancount)
  5. Optionally generate a payment link via the payment layer
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction as db_transaction

from apps.core.models import Entity

from ..models import Invoice, InvoiceLineItem

logger = logging.getLogger(__name__)


def create_invoice(
    entity_slug: str,
    customer: dict,
    line_items: list[dict],
    currency: str = "USD",
    due_days: int = 30,
    auto_collect: bool = False,
    processor: str | None = None,
    notes: str = "",
    created_by=None,
) -> Invoice:
    """
    Create an invoice with line items.

    Args:
        entity_slug:     Entity that owns the invoice
        customer:        {"id": str, "email": str, "name": str}
        line_items:      [{"description": str, "quantity": num, "unit_price": num, ...}]
        currency:        ISO 4217 currency code
        due_days:        Days until invoice is due
        auto_collect:    If True, generate a payment link immediately
        processor:       Preferred payment processor for auto_collect
        notes:           Invoice notes
        created_by:      User who created the invoice

    Returns:
        Created Invoice instance
    """
    entity = Entity.objects.get(slug=entity_slug)

    with db_transaction.atomic():
        # 1. Generate invoice number
        invoice_number = _generate_invoice_number(entity)

        # 2. Create invoice
        invoice = Invoice.objects.create(
            number=invoice_number,
            entity=entity,
            customer_name=customer.get("name", ""),
            customer_email=customer.get("email", ""),
            customer_id=customer.get("id", ""),
            currency=currency,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=due_days),
            notes=notes,
            preferred_processor=processor or "",
            created_by=created_by,
        )

        # 3. Create line items
        for item in line_items:
            InvoiceLineItem.objects.create(
                invoice=invoice,
                description=item.get("description", ""),
                quantity=Decimal(str(item.get("quantity", 1))),
                unit_price=Decimal(str(item.get("unit_price", 0))),
                tax_rate=Decimal(str(item.get("tax_rate", 0))),
                category=item.get("category", "General"),
            )

        # 4. Calculate totals
        invoice.recalculate()

        # 5. Post accounting entries to beancount
        _post_invoice_to_beancount(invoice)

        # 6. Auto-collect: generate payment link
        if auto_collect:
            _generate_payment_link(invoice, processor)

        # 7. Set status
        invoice.status = Invoice.Status.PENDING if hasattr(Invoice, 'Status') else "pending"
        invoice.save(update_fields=["status", "updated_at"])

    logger.info(
        "Created invoice %s (%s %s, %d line items, auto_collect=%s)",
        invoice.number, invoice.total, invoice.currency,
        len(line_items), auto_collect,
    )
    return invoice


def _generate_invoice_number(entity: Entity) -> str:
    """Generate the next sequential invoice number for an entity."""
    last = Invoice.objects.filter(
        entity=entity,
    ).order_by("-created_at").first()

    next_num = 1
    if last:
        try:
            next_num = int(last.number.split("-")[-1]) + 1
        except (ValueError, IndexError):
            next_num = Invoice.objects.filter(entity=entity).count() + 1

    prefix = entity.slug.upper()[:10]
    return f"INV-{prefix}-{next_num:06d}"


def _post_invoice_to_beancount(invoice: Invoice):
    """Create a beancount entry for the invoice."""
    try:
        from apps.accounting.beancount.sync import BeancountSyncService
        BeancountSyncService.sync_invoice(invoice)
    except Exception as e:
        logger.warning("Beancount sync failed for invoice %s: %s", invoice.number, e)
        # Don't fail invoice creation because of beancount


def _generate_payment_link(invoice: Invoice, processor: str | None = None):
    """Prepare a payment through the unified payment layer."""
    try:
        from apps.core.utils import generate_idempotency_key
        from apps.payments.flows import FinsioPaymentFlow
        from apps.payments.models import Payment
        from apps.core.choices import PaymentStatus

        idem_key = generate_idempotency_key(
            "invoice", str(invoice.id), str(invoice.total), invoice.currency,
        )

        payment, created = Payment.objects.get_or_create(
            idempotency_key=idem_key,
            defaults={
                "amount": invoice.total,
                "currency": invoice.currency,
                "description": f"Payment for {invoice.number}",
                "reference": invoice.number,
                "customer_id": invoice.customer_id,
                "customer_email": invoice.customer_email,
                "invoice": invoice,
                "status": PaymentStatus.NEW,
            },
        )

        if created:
            flow = FinsioPaymentFlow()
            result = flow.prepare(
                payment,
                processor or invoice.preferred_processor or "stripe",
            )
            invoice.payment_url = result.get("redirect_url", "")
            invoice.save(update_fields=["payment_url", "updated_at"])

            logger.info("Payment link generated for invoice %s", invoice.number)

    except Exception as e:
        logger.exception("Failed to generate payment link for invoice %s", invoice.number)
