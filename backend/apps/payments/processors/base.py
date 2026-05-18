"""
Abstract base class for all Finsio payment processors.

Every processor must implement:
  - prepare_transaction(): initiate a payment with the provider
  - handle_webhook():      process an incoming webhook notification
  - refund():              refund a completed payment

The base class provides:
  - getpaid-core compatibility via _build_getpaid_processor()
  - Shared accepted_currencies and display_name attributes
  - Optional verify_signature() override for webhook security
"""

from __future__ import annotations

import abc
import logging
from decimal import Decimal
from typing import Any

logger = logging.getLogger(__name__)


class FinsioBaseProcessor(abc.ABC):
    """
    Abstract base for all Finsio payment processors.

    Subclasses MUST set:
      - slug:                 str  (e.g. "stripe")
      - display_name:         str  (e.g. "Stripe")
      - accepted_currencies:  list (e.g. ["USD", "EUR", "GBP"])
    """

    slug: str = ""
    display_name: str = ""
    accepted_currencies: list[str] = ["USD"]

    @abc.abstractmethod
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
        Initiate a payment with the provider.

        Returns a dict with at least:
            {
                "redirect_url": str | None,
                "method": str  ("GET" or "POST"),
                "data": dict   (provider-specific: intent ID, client token, etc.)
            }

        Raises:
            RuntimeError or provider-specific exception on failure.
        """
        ...

    @abc.abstractmethod
    async def handle_webhook(
        self,
        headers: dict[str, str],
        body: bytes,
    ) -> dict[str, Any]:
        """
        Process an incoming webhook from this provider.

        The implementation MUST verify the webhook signature.

        Returns a normalized dict:
            {
                "status": "paid" | "failed" | "refunded" | "ignored" | "error",
                "external_id": str | None,
                "event_id": str | None,
                "metadata": dict,
            }
        """
        ...

    @abc.abstractmethod
    async def refund(
        self,
        external_id: str,
        amount: Decimal | None = None,
        reason: str = "",
    ) -> dict[str, Any]:
        """
        Refund a payment.

        Args:
            external_id: Provider's payment/charge ID
            amount:      Partial refund amount (None = full refund)
            reason:      Human-readable refund reason

        Returns:
            {"external_id": str, "status": str, "amount": ...}
        """
        ...

    async def verify_signature(
        self,
        headers: dict[str, str],
        body: bytes,
    ) -> bool:
        """
        Verify webhook signature. Default accepts all.

        Override in subclasses to implement provider-specific
        signature verification.
        """
        return True

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} slug={self.slug}>"
