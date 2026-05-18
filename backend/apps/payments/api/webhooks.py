"""
Webhook receivers for payment providers.

Handles incoming webhook notifications from Stripe, PayPal,
Braintree, and Authorize.Net. Each webhook is:
  1. Verified (signature check by the processor)
  2. Parsed into a normalized status dict
  3. Used to update the Payment record via FinsioPaymentFlow

All webhooks return 200 to avoid provider retry storms,
even on processing errors (errors are logged).
"""

import asyncio
import logging

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response

from apps.core.choices import PaymentStatus

from ..flows import FinsioPaymentFlow
from ..models import Payment
from ..registry import get_registry

logger = logging.getLogger(__name__)


@api_view(["POST"])
@permission_classes([AllowAny])
def payment_webhook(request: Request, provider: str) -> Response:
    """
    POST /webhooks/payments/{provider}

    Receives raw webhook payloads from payment providers.
    The processor implementation handles signature verification.
    """
    registry = get_registry()

    # Resolve the processor
    try:
        processor = registry.get(provider)
    except ValueError:
        logger.warning("Webhook received for unknown provider: %s", provider)
        return Response({"received": True}, status=200)

    # Build headers dict from Django META
    headers = {}
    for key, value in request.META.items():
        if key.startswith("HTTP_"):
            header_name = key[5:].lower().replace("_", "-")
            headers[header_name] = value
    headers["content-type"] = request.META.get("CONTENT_TYPE", "")

    # Let the processor handle signature verification and parsing
    try:
        result = asyncio.run(
            processor.handle_webhook(headers=headers, body=request.body)
        )
    except Exception as e:
        logger.exception("Webhook processing error for %s: %s", provider, e)
        return Response({"received": True}, status=200)

    # Ignore events we don't handle
    if result.get("status") == "ignored":
        logger.debug("Ignored webhook event from %s: %s", provider, result.get("event_type"))
        return Response({"received": True}, status=200)

    # Log errors but still acknowledge
    if result.get("status") == "error":
        logger.warning("Webhook error from %s: %s", provider, result.get("error"))
        return Response({"received": True}, status=200)

    # Find the payment by external_id
    external_id = result.get("external_id")
    if not external_id:
        logger.warning("Webhook from %s missing external_id", provider)
        return Response({"received": True}, status=200)

    try:
        payment = Payment.objects.get(external_id=external_id)
    except Payment.DoesNotExist:
        logger.warning(
            "No payment found for external_id=%s from %s",
            external_id, provider,
        )
        return Response({"received": True}, status=200)

    # Update payment status
    flow = FinsioPaymentFlow()
    event_id = result.get("event_id")

    if result["status"] == "paid":
        flow.confirm_paid(
            payment=payment,
            external_id=external_id,
            provider_event_id=event_id,
            metadata=result.get("metadata"),
        )
    elif result["status"] == "failed":
        failure_msg = result.get("metadata", {}).get("failure_message", "")
        flow.confirm_failed(
            payment=payment,
            reason=failure_msg,
            provider_event_id=event_id,
            metadata=result.get("metadata"),
        )
    elif result["status"] == "refunded":
        refund_amount = result.get("metadata", {}).get("refund_amount", 0)
        payment.mark_refunded(
            refund_id=result.get("metadata", {}).get("refund_id", ""),
            amount=refund_amount,
            metadata=result.get("metadata"),
        )

    return Response({"received": True}, status=200)
