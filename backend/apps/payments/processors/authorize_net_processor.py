"""
Authorize.Net payment processor for Finsio.

Uses the authorizenet SDK for:
  - Hosted payment page / Accept.js integration
  - Webhook (webhook notification) processing
  - Transaction refunds

Authorize.Net supports both direct server-side charges
and a hosted payment form (Accept.js / Accept Hosted).
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from django.conf import settings

from .base import FinsioBaseProcessor

logger = logging.getLogger(__name__)


class AuthorizeNetProcessor(FinsioBaseProcessor):
    """Authorize.Net payment processor."""

    slug = "authorize_net"
    display_name = "Authorize.Net"
    accepted_currencies = ["USD", "CAD", "GBP", "EUR", "AUD"]

    def __init__(self):
        self.api_login_id = getattr(settings, "AUTHORIZE_NET_LOGIN_ID", "")
        self.transaction_key = getattr(settings, "AUTHORIZE_NET_TRANSACTION_KEY", "")
        self.sandbox = settings.DEBUG

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
        Prepare a transaction via Accept Hosted or Accept.js.

        Returns the data needed by the frontend to render the
        Authorize.Net payment form.
        """
        try:
            from authorizenet import apicontractsv1
            from authorizenet.apicontrollers import (
                createTransactionController,
            )

            # Build the transaction request
            merchant_auth = apicontractsv1.merchantAuthenticationType()
            merchant_auth.name = self.api_login_id
            merchant_auth.transactionKey = self.transaction_key

            transaction_request = apicontractsv1.transactionRequestType()
            transaction_request.transactionType = "authCaptureTransaction"
            transaction_request.amount = float(amount)

            # Customer info
            customer = apicontractsv1.customerDataType()
            customer.email = customer_email
            transaction_request.customer = customer

            # Order info
            transaction_request.order = apicontractsv1.orderType()
            transaction_request.order.invoiceNumber = reference[:20]
            transaction_request.order.description = description[:255]

            # Create the request
            create_request = apicontractsv1.createTransactionRequest()
            create_request.merchantAuthentication = merchant_auth
            create_request.refId = reference
            create_request.transactionRequest = transaction_request

            controller = createTransactionController(create_request)

            logger.info(
                "Authorize.Net transaction prepared for %s %s (ref: %s)",
                amount, currency, reference,
            )

            return {
                "redirect_url": None,
                "method": "POST",
                "data": {
                    "reference": reference,
                    "amount": str(amount),
                    "currency": currency,
                    "api_login_id": self.api_login_id,
                    "environment": "sandbox" if self.sandbox else "production",
                },
            }

        except ImportError:
            logger.warning("authorizenet SDK not installed — returning stub")
            return {
                "redirect_url": None,
                "method": "POST",
                "data": {
                    "reference": reference,
                    "amount": str(amount),
                    "currency": currency,
                    "stub": True,
                    "message": "authorizenet SDK not installed",
                },
            }

    async def handle_webhook(
        self,
        headers: dict[str, str],
        body: bytes,
    ) -> dict[str, Any]:
        """
        Process an Authorize.Net webhook notification.

        Authorize.Net sends HMAC-SHA512 signatures in the
        X-ANET-Signature header.
        """
        import hashlib
        import hmac
        import json

        # Verify signature
        signature_header = headers.get("x-anet-signature", "")
        if self.transaction_key and signature_header:
            expected = hmac.new(
                self.transaction_key.encode(),
                body,
                hashlib.sha512,
            ).hexdigest()
            expected_formatted = f"SHA512={expected}"

            if not hmac.compare_digest(signature_header, expected_formatted):
                logger.warning("Authorize.Net webhook signature mismatch")
                return {"status": "error", "error": "Invalid signature"}

        try:
            event = json.loads(body)
        except json.JSONDecodeError:
            return {"status": "error", "error": "Invalid JSON"}

        event_type = event.get("eventType", "")
        payload = event.get("payload", {})

        if "net.authorize.payment.authcapture.created" in event_type:
            return {
                "status": "paid",
                "external_id": str(payload.get("id", "")),
                "event_id": event.get("eventId", ""),
                "metadata": {
                    "response_code": payload.get("responseCode"),
                    "auth_amount": payload.get("authAmount"),
                },
            }

        if "net.authorize.payment.failed" in event_type:
            return {
                "status": "failed",
                "external_id": str(payload.get("id", "")),
                "event_id": event.get("eventId", ""),
                "metadata": {
                    "response_code": payload.get("responseCode"),
                    "response_text": payload.get("responseText", ""),
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
        Refund an Authorize.Net transaction.

        Args:
            external_id: Authorize.Net transaction ID
            amount:      Partial refund amount (None = full)
        """
        try:
            from authorizenet import apicontractsv1
            from authorizenet.apicontrollers import createTransactionController

            merchant_auth = apicontractsv1.merchantAuthenticationType()
            merchant_auth.name = self.api_login_id
            merchant_auth.transactionKey = self.transaction_key

            transaction_request = apicontractsv1.transactionRequestType()
            transaction_request.transactionType = "refundTransaction"
            transaction_request.refTransId = external_id

            if amount is not None:
                transaction_request.amount = float(amount)

            create_request = apicontractsv1.createTransactionRequest()
            create_request.merchantAuthentication = merchant_auth
            create_request.transactionRequest = transaction_request

            controller = createTransactionController(create_request)
            controller.execute()

            response = controller.getresponse()

            if response and response.messages.resultCode == "Ok":
                return {
                    "external_id": external_id,
                    "status": "refunded",
                    "amount": str(amount) if amount else "full",
                }

            return {
                "external_id": external_id,
                "status": "failed",
                "error": str(response.messages.message[0].text) if response else "Unknown error",
            }

        except ImportError:
            logger.warning("authorizenet SDK not installed")
            return {
                "external_id": external_id,
                "status": "stub",
                "message": "authorizenet SDK not installed",
            }
