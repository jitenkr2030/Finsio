"""
PayPal payment processor for Finsio.

Uses paypalrestsdk for:
  - Payment creation and approval flow
  - Webhook event verification
  - Sale refunds

PayPal requires a redirect flow: the customer is sent to
PayPal's site to approve the payment, then redirected back.
"""

from __future__ import annotations

import json
import logging
from decimal import Decimal
from typing import Any

import paypalrestsdk
from django.conf import settings

from .base import FinsioBaseProcessor

logger = logging.getLogger(__name__)


class PayPalProcessor(FinsioBaseProcessor):
    """PayPal payment processor."""

    slug = "paypal"
    display_name = "PayPal"
    accepted_currencies = ["USD", "EUR", "GBP", "CAD", "AUD", "JPY", "CHF", "SEK", "NOK"]

    def __init__(self):
        paypalrestsdk.configure({
            "mode": settings.PAYPAL_MODE,
            "client_id": settings.PAYPAL_CLIENT_ID,
            "client_secret": settings.PAYPAL_CLIENT_SECRET,
        })

    async def prepare_transaction(
        self,
        amount: Decimal,
        currency: str,
        description: str,
        reference: str,
        customer_email: str,
        callback_url: str | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Create a PayPal payment and return the approval URL.

        The customer must be redirected to the approval_url to
        complete payment on PayPal's site.
        """
        return_url = callback_url or f"/api/v1/payments/paypal/success"
        cancel_url = callback_url or f"/api/v1/payments/paypal/cancel"

        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {"payment_method": "paypal"},
            "redirect_urls": {
                "return_url": return_url,
                "cancel_url": cancel_url,
            },
            "transactions": [{
                "amount": {
                    "total": str(amount),
                    "currency": currency,
                },
                "description": description[:127],
                "invoice_number": reference[:127],
                "payee": {
                    "email": customer_email,
                },
            }],
        })

        if not payment.create():
            error_msg = payment.error.get("message", "Unknown PayPal error")
            logger.error("PayPal payment creation failed: %s", error_msg)
            raise RuntimeError(f"PayPal error: {error_msg}")

        # Extract the approval URL
        approval_url = None
        for link in payment.links:
            if link.rel == "approval_url":
                approval_url = link.href
                break

        logger.info("PayPal payment created: %s", payment.id)

        return {
            "redirect_url": approval_url,
            "method": "GET",
            "data": {
                "paypal_payment_id": payment.id,
                "approval_url": approval_url,
            },
        }

    async def handle_webhook(
        self,
        headers: dict[str, str],
        body: bytes,
    ) -> dict[str, Any]:
        """
        Process a PayPal webhook event.

        Note: PayPal webhook signature verification requires
        the webhook ID configured in the PayPal dashboard.
        """
        try:
            event = json.loads(body)
        except json.JSONDecodeError:
            return {"status": "error", "error": "Invalid JSON"}

        event_type = event.get("event_type", "")
        resource = event.get("resource", {})

        if event_type == "PAYMENT.SALE.COMPLETED":
            return {
                "status": "paid",
                "external_id": resource.get("id", ""),
                "event_id": event.get("id", ""),
                "metadata": {
                    "paypal_payment_id": resource.get("parent_payment", ""),
                    "amount": resource.get("amount", {}).get("total"),
                    "currency": resource.get("amount", {}).get("currency"),
                    "payer_email": resource.get("payer", {}).get("payer_info", {}).get("email"),
                },
            }

        if event_type == "PAYMENT.SALE.DENIED":
            return {
                "status": "failed",
                "external_id": resource.get("id", ""),
                "event_id": event.get("id", ""),
                "metadata": {
                    "failure_message": resource.get("reason_code", "denied"),
                },
            }

        if event_type == "PAYMENT.SALE.REFUNDED":
            return {
                "status": "refunded",
                "external_id": resource.get("parent_payment", ""),
                "event_id": event.get("id", ""),
                "metadata": {
                    "refund_id": resource.get("id", ""),
                    "refund_amount": resource.get("amount", {}).get("total"),
                },
            }

        return {"status": "ignored", "event_type": event_type}

    async def refund(
        self,
        external_id: str,
        amount: Decimal | None = None,
        reason: str = "",
    ) -> dict[str, Any]:
        """
        Refund a PayPal sale.

        Args:
            external_id: PayPal sale ID
            amount:      Partial refund amount (None = full)
        """
        sale = paypalrestsdk.Sale.find(external_id)

        refund_data: dict[str, Any] = {}
        if amount is not None:
            refund_data["amount"] = {
                "total": str(amount),
                "currency": "USD",  # Should match original currency
            }

        refund = sale.refund(refund_data)

        if not refund.success():
            raise RuntimeError(f"PayPal refund failed: {refund.error}")

        logger.info("PayPal refund created: %s for sale %s", refund.id, external_id)

        return {
            "external_id": refund.id,
            "status": refund.state,
            "amount": refund.amount.get("total") if refund.amount else None,
        }
