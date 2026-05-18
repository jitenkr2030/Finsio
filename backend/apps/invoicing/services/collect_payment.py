"""
Payment collection service for Finsio.

Provides payment status queries for invoices
and handles partial payment tracking.
"""

from __future__ import annotations

import logging
from decimal import Decimal

from ..models import Invoice
from apps.payments.models import Payment

logger = logging.getLogger(__name__)


def get_invoice_payment_status(invoice: Invoice) -> dict:
    """
    Get the payment status summary for an invoice.

    Returns:
        {
            "invoice_id": str,
            "invoice_number": str,
            "total": str,
            "amount_paid": str,
            "amount_due": str,
            "status": str,
            "payment_url": str | None,
            "payments": [...],
        }
    """
    payments = Payment.objects.filter(invoice=invoice).order_by("-created_at")

    return {
        "invoice_id": str(invoice.id),
        "invoice_number": invoice.number,
        "total": str(invoice.total),
        "amount_paid": str(invoice.amount_paid),
        "amount_due": str(invoice.amount_due),
        "status": invoice.status,
        "payment_url": invoice.payment_url,
        "currency": invoice.currency,
        "payments": [
            {
                "payment_id": str(p.id),
                "status": p.status,
                "amount": str(p.amount),
                "processor": p.processor,
                "external_id": p.external_id,
                "paid_at": p.paid_at.isoformat() if p.paid_at else None,
                "created_at": p.created_at.isoformat(),
            }
            for p in payments
        ],
    }


def calculate_outstanding_invoices(entity_slug: str) -> dict:
    """
    Calculate total outstanding amounts for an entity.
    """
    from django.db.models import Sum

    outstanding = Invoice.objects.filter(
        entity__slug=entity_slug,
        status__in=["pending", "partial", "overdue"],
    ).aggregate(
        total_due=Sum("amount_due"),
        invoice_count=Count("id"),
    )

    overdue = Invoice.objects.filter(
        entity__slug=entity_slug,
        status="overdue",
    ).aggregate(
        overdue_amount=Sum("amount_due"),
        overdue_count=Count("id"),
    )

    return {
        "entity": entity_slug,
        "total_outstanding": str(outstanding["total_due"] or 0),
        "outstanding_count": outstanding["invoice_count"],
        "overdue_amount": str(overdue["overdue_amount"] or 0),
        "overdue_count": overdue["overdue_count"],
    }


# Needed for aggregate queries
from django.db.models import Count
