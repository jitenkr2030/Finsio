"""
Payment flow orchestration for Finsio.

Wraps python-getpaid-core's PaymentFlow state machine
and translates between its abstract PaymentStatus enum
and our concrete Payment model's status field.

getpaid_core.PaymentStatus values:
  NEW, PREPARED, PRE_AUTH, IN_CHARGE, PAID,
  PARTIAL, FAILED, REFUND_STARTED, REFUNDED
"""

from __future__ import annotations

import logging
from typing import Any

from django.db import transaction as db_transaction

from getpaid_core import PaymentFlow, PaymentStatus

from apps.core.choices import PaymentStatus as FinsioStatus

from .models import Payment, PaymentEvent

logger = logging.getLogger(__name__)


class FinsioPaymentFlow:
    """
    Orchestrates payment state transitions via getpaid_core.

    Methods:
        prepare()       -> NEW -> PREPARED
        confirm_paid()  -> * -> PAID (idempotent)
        confirm_failed() -> * -> FAILED
    """

    # Map getpaid_core states to our model states
    STATUS_MAP = {
        PaymentStatus.NEW: FinsioStatus.NEW,
        PaymentStatus.PREPARED: FinsioStatus.PREPARED,
        PaymentStatus.PRE_AUTH: FinsioStatus.IN_PROGRESS,
        PaymentStatus.IN_CHARGE: FinsioStatus.IN_PROGRESS,
        PaymentStatus.PAID: FinsioStatus.PAID,
        PaymentStatus.PARTIAL: FinsioStatus.PAID,
        PaymentStatus.FAILED: FinsioStatus.FAILED,
        PaymentStatus.REFUND_STARTED: FinsioStatus.IN_PROGRESS,
        PaymentStatus.REFUNDED: FinsioStatus.REFUNDED,
    }

    def __init__(self):
        self._flow = PaymentFlow()

    def prepare(
        self,
        payment: Payment,
        processor_slug: str,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Transition a payment from NEW to PREPARED.

        Calls the processor to create a checkout session or
        payment intent and stores the redirect URL.
        """
        if payment.is_terminal:
            raise ValueError(
                f"Cannot prepare payment {payment.id}: "
                f"already in terminal state '{payment.status}'"
            )

        with db_transaction.atomic():
            getpaid_payment = self._to_getpaid_payment(payment)

            result = self._flow.prepare(
                getpaid_payment,
                backend=processor_slug,
                **kwargs,
            )

            redirect_url = getattr(result, "redirect_url", None)
            extra_data = getattr(result, "extra_data", {})

            old_status = payment.status
            payment.processor = processor_slug
            payment.status = FinsioStatus.PREPARED
            payment.redirect_url = redirect_url
            payment.save(update_fields=[
                "processor", "status", "redirect_url", "updated_at",
            ])

            self._record_event(
                payment=payment,
                event_type=PaymentEvent.EventType.PREPARED,
                old_status=old_status,
                new_status=FinsioStatus.PREPARED,
                data={
                    "processor": processor_slug,
                    "redirect_url": redirect_url,
                    **extra_data,
                },
            )

            logger.info(
                "Payment %s prepared with %s (redirect: %s)",
                payment.id, processor_slug, redirect_url,
            )

        return {
            "redirect_url": redirect_url,
            "method": getattr(result, "method", "GET"),
            "data": extra_data,
        }

    def confirm_paid(
        self,
        payment: Payment,
        external_id: str,
        provider_event_id: str | None = None,
        metadata: dict | None = None,
    ) -> Payment:
        """
        Transition a payment to PAID status.

        Idempotent: duplicate provider_event_id is skipped.
        """
        with db_transaction.atomic():
            old_status = payment.status

            if provider_event_id and PaymentEvent.objects.filter(
                provider_event_id=provider_event_id,
            ).exists():
                logger.info(
                    "Skipping duplicate provider event %s for payment %s",
                    provider_event_id, payment.id,
                )
                return payment

            payment.mark_paid(external_id=external_id, metadata=metadata)

            self._record_event(
                payment=payment,
                event_type=PaymentEvent.EventType.STATUS_CHANGED,
                old_status=old_status,
                new_status=FinsioStatus.PAID,
                provider_event_id=provider_event_id,
                data={"external_id": external_id, **(metadata or {})},
            )

            logger.info(
                "Payment %s confirmed paid (ext: %s, was: %s)",
                payment.id, external_id, old_status,
            )

        return payment

    def confirm_failed(
        self,
        payment: Payment,
        reason: str = "",
        provider_event_id: str | None = None,
        metadata: dict | None = None,
    ) -> Payment:
        """Transition a payment to FAILED status."""
        with db_transaction.atomic():
            old_status = payment.status

            if provider_event_id and PaymentEvent.objects.filter(
                provider_event_id=provider_event_id,
            ).exists():
                logger.info(
                    "Skipping duplicate failure event %s for payment %s",
                    provider_event_id, payment.id,
                )
                return payment

            payment.mark_failed(reason=reason, metadata=metadata)

            self._record_event(
                payment=payment,
                event_type=PaymentEvent.EventType.STATUS_CHANGED,
                old_status=old_status,
                new_status=FinsioStatus.FAILED,
                provider_event_id=provider_event_id,
                data={"reason": reason, **(metadata or {})},
            )

            logger.warning(
                "Payment %s confirmed failed (reason: %s)",
                payment.id, reason,
            )

        return payment

    def _to_getpaid_payment(self, payment: Payment):
        """
        Convert our Payment model to a getpaid_core payment object.

        getpaid_core expects an object with at minimum: pk, amount, currency.
        """
        getpaid_obj = self._flow.create_payment_object()
        getpaid_obj.pk = str(payment.id)
        getpaid_obj.amount = payment.amount
        getpaid_obj.currency = payment.currency
        getpaid_obj.description = payment.description
        return getpaid_obj

    def _record_event(
        self,
        payment: Payment,
        event_type: str,
        old_status: str = "",
        new_status: str = "",
        provider_event_id: str | None = None,
        data: dict | None = None,
    ):
        """Create an immutable audit log entry."""
        PaymentEvent.objects.create(
            payment=payment,
            event_type=event_type,
            old_status=old_status,
            new_status=new_status,
            provider_event_id=provider_event_id,
            data=data or {},
        )
