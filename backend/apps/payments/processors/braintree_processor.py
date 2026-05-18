"""
Braintree (PayPal-owned) payment processor for Finsio.

Braintree uses a client-token flow: the frontend gets a
token, renders a payment form (Drop-in UI), and submits
a nonce to our backend for server-side transaction creation.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

import braintree
from django.conf import settings

from .base import FinsioBaseProcessor

logger = logging.getLogger(__name__)


class BraintreeProcessor(FinsioBaseProcessor):
    """Braintree payment processor."""

    slug = "braintree"
    display_name = "Braintree"
    accepted_currencies = ["USD", "EUR", "GBP", "AUD", "CAD"]

    def __init__(self):
        environment = (
            braintree.Environment.Sandbox
            if settings.DEBUG
            else braintree.Environment.Production
        )
        self.gateway = braintree.BraintreeGateway(
            braintree.Configuration(
                environment,
                merchant_id=settings.BRAINTREE_MERCHANT_ID,
                public_key=settings.BRAINTREE_PUBLIC_KEY,
                private_key=settings.BRAINTREE_PRIVATE_KEY,
            )
        )

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
        Generate a Braintree client token for the frontend.

        The client-side Drop-in UI uses this token to render
        the payment form. The actual transaction is created
        after the customer submits their payment nonce.
        """
        client_token = self.gateway.client_token.generate({
            "merchant_account_id": currency if currency != "USD" else None,
        })

        logger.info(
            "Braintree client token generated for %s %s",
            amount, currency,
        )

        return {
            "redirect_url": None,
            "method": "POST",
            "data": {
                "client_token": client_token,
                "amount": str(amount),
                "currency": currency,
                "reference": reference,
            },
        }

    async def handle_webhook(
        self,
        headers: dict[str, str],
        body: bytes,
    ) -> dict[str, Any]:
        """
        Process a Braintree webhook notification.

        Braintree webhooks use a bt_signature and bt_payload
        passed as form data (not JSON).
        """
        bt_signature = headers.get("bt-signature", "")
        bt_payload = headers.get("bt-payload", "")

        if not bt_signature or not bt_payload:
            # Try parsing from body as form data
            try:
                import urllib.parse
                parsed = urllib.parse.parse_qs(body.decode())
                bt_signature = parsed.get("bt_signature", [""])[0]
                bt_payload = parsed.get("bt_payload", [""])[0]
            except Exception:
                return {"status": "error", "error": "Missing bt_signature or bt_payload"}

        try:
            notification = self.gateway.webhook_notification.parse(
                bt_signature, bt_payload,
            )
        except Exception as e:
            logger.warning("Braintree webhook parse failed: %s", e)
            return {"status": "error", "error": str(e)}

        kind = notification.kind
        txn = notification.transaction

        if kind == braintree.WebhookNotification.Kind.SubscriptionChargedSuccessfully:
            return {
                "status": "paid",
                "external_id": txn.id if txn else "",
                "event_id": str(notification.timestamp.timestamp()),
                "metadata": {
                    "kind": kind,
                    "amount": str(txn.amount) if txn else None,
                    "currency": txn.currency_iso_code if txn else None,
                },
            }

        if kind == braintree.WebhookNotification.Kind.SubscriptionChargedUnsuccessfully:
            return {
                "status": "failed",
                "external_id": txn.id if txn else "",
                "event_id": str(notification.timestamp.timestamp()),
                "metadata": {
                    "kind": kind,
                    "status": txn.status if txn else "unknown",
                },
            }

        if kind == braintree.WebhookNotification.Kind.TransactionDisbursed:
            return {
                "status": "paid",
                "external_id": txn.id if txn else "",
                "event_id": str(notification.timestamp.timestamp()),
                "metadata": {"kind": kind},
            }

        return {"status": "ignored", "kind": kind}

    async def refund(
        self,
        external_id: str,
        amount: Decimal | None = None,
        reason: str = "",
    ) -> dict[str, Any]:
        """
        Refund a Braintree transaction.

        Args:
            external_id: Braintree transaction ID
            amount:      Partial refund amount (None = full)
        """
        kwargs = {}
        if amount is not None:
            kwargs["amount"] = str(amount)

        result = self.gateway.transaction.refund(external_id, **kwargs)

        if result.is_success:
            logger.info("Braintree refund successful: %s", result.transaction.id)
            return {
                "success": True,
                "external_id": result.transaction.id,
                "status": result.transaction.status,
                "amount": str(result.transaction.amount),
            }

        logger.warning("Braintree refund failed: %s", result.message)
        return {
            "success": False,
            "external_id": None,
            "status": "failed",
            "error": result.message,
        }
