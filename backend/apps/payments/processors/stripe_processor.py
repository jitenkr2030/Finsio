"""
Stripe payment processor for Finsio.

Uses the stripe-python SDK for:
  - PaymentIntent creation (prepare_transaction)
  - Webhook event verification and parsing (handle_webhook)
  - Refunds (refund)

Bridges with:
  - python-getpaid-core's BaseProcessor interface
  - Direct Stripe API via stripe.PaymentIntent
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

import stripe
from django.conf import settings

from apps.core.utils import to_minor_units

from .base import FinsioBaseProcessor

logger = logging.getLogger(__name__)


class StripeProcessor(FinsioBaseProcessor):
    """Stripe payment processor."""

    slug = "stripe"
    display_name = "Stripe"
    accepted_currencies = [
        "USD", "EUR", "GBP", "CAD", "AUD", "JPY", "CHF",
        "SEK", "NOK", "DKK", "NZD", "SGD", "HKD", "MXN",
    ]

    def __init__(self):
        stripe.api_key = settings.STRIPE_SECRET_KEY

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
        Create a Stripe PaymentIntent and return the checkout URL.

        The client_secret is returned so the frontend can open
        Stripe's embedded checkout, or a redirect_url for hosted checkout.
        """
        intent = stripe.PaymentIntent.create(
            amount=to_minor_units(amount, currency),
            currency=currency.lower(),
            description=description,
            receipt_email=customer_email,
            metadata={
                "reference": reference,
                "finsio": "true",
            },
            automatic_payment_methods={"enabled": True},
        )

        logger.info(
            "Stripe PaymentIntent created: %s (amount: %s %s)",
            intent.id, amount, currency,
        )

        return {
            "redirect_url": None,  # Client-side Stripe.js handles redirect
            "method": "POST",
            "data": {
                "payment_intent_id": intent.id,
                "client_secret": intent.client_secret,
                "amount_minor": intent.amount,
                "currency": intent.currency,
            },
        }

    async def handle_webhook(
        self,
        headers: dict[str, str],
        body: bytes,
    ) -> dict[str, Any]:
        """
        Verify and process a Stripe webhook event.

        Supported events:
          - payment_intent.succeeded → paid
          - payment_intent.payment_failed → failed
          - charge.refunded → refunded
        """
        sig_header = headers.get("stripe-signature", "")

        # Verify signature
        try:
            event = stripe.Webhook.construct_event(
                body, sig_header, settings.STRIPE_WEBHOOK_SECRET,
            )
        except ValueError:
            logger.warning("Stripe webhook: invalid payload")
            return {"status": "error", "error": "Invalid payload"}
        except stripe.error.SignatureVerificationError:
            logger.warning("Stripe webhook: invalid signature")
            return {"status": "error", "error": "Invalid signature"}

        event_type = event.type
        obj = event.data.object

        if event_type == "payment_intent.succeeded":
            return {
                "status": "paid",
                "external_id": obj.id,
                "event_id": event.id,
                "metadata": {
                    "amount_received": obj.amount_received,
                    "currency": obj.currency,
                    "customer_email": obj.receipt_email,
                    "payment_method": obj.payment_method,
                },
            }

        if event_type == "payment_intent.payment_failed":
            error = obj.last_payment_error or {}
            return {
                "status": "failed",
                "external_id": obj.id,
                "event_id": event.id,
                "metadata": {
                    "failure_message": error.get("message", "Unknown error"),
                    "failure_code": error.get("code", ""),
                    "failure_type": error.get("type", ""),
                },
            }

        if event_type == "charge.refunded":
            return {
                "status": "refunded",
                "external_id": obj.payment_intent,
                "event_id": event.id,
                "metadata": {
                    "refund_id": obj.id,
                    "refund_amount": obj.amount_refunded,
                    "currency": obj.currency,
                },
            }

        # Unhandled event type
        return {"status": "ignored", "event_type": event_type}

    async def refund(
        self,
        external_id: str,
        amount: Decimal | None = None,
        reason: str = "",
    ) -> dict[str, Any]:
        """
        Create a Stripe refund for a PaymentIntent.

        Args:
            external_id: Stripe PaymentIntent ID (pi_xxx)
            amount:      Partial amount to refund (None = full)
            reason:      Refund reason (duplicate, fraudulent, requested_by_customer)
        """
        refund_kwargs: dict[str, Any] = {
            "payment_intent": external_id,
        }

        if amount is not None:
            refund_kwargs["amount"] = to_minor_units(amount)

        if reason:
            # Stripe accepts: duplicate, fraudulent, requested_by_customer
            stripe_reason = {
                "duplicate": "duplicate",
                "fraud": "fraudulent",
                "customer_request": "requested_by_customer",
            }.get(reason, "requested_by_customer")
            refund_kwargs["reason"] = stripe_reason

        refund_obj = stripe.Refund.create(**refund_kwargs)

        logger.info(
            "Stripe refund created: %s for PaymentIntent %s (amount: %s)",
            refund_obj.id, external_id, amount,
        )

        return {
            "external_id": refund_obj.id,
            "status": refund_obj.status,
            "amount": refund_obj.amount,
        }
