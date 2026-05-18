"""
django-merchant provider wrappers for Finsio.

Wraps merchant.billing to provide a consistent interface
for direct card charges that complements getpaid-core's
redirect-based PaymentFlow.

Usage:
    provider = get_merchant_provider("stripe")
    result = provider.charge(amount=Decimal("49.99"), credit_card=card)
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

logger = logging.getLogger(__name__)


class MerchantProviderWrapper:
    """
    Wraps a django-merchant billing provider into a consistent interface.

    Provides: charge, authorize, capture, refund, recurring
    """

    def __init__(self, provider_name: str):
        self.provider_name = provider_name
        self._provider = None

    def _get_provider(self):
        if self._provider is None:
            try:
                from merchant.billing import get_provider
                self._provider = get_provider(self.provider_name)
                logger.info("Loaded merchant provider: %s", self.provider_name)
            except ImportError:
                logger.warning("merchant library not installed")
                raise
            except Exception as e:
                logger.error("Failed to load merchant provider %s: %s", self.provider_name, e)
                raise
        return self._provider

    def charge(self, amount: Decimal, credit_card: dict | None = None, options: dict | None = None) -> dict[str, Any]:
        provider = self._get_provider()
        try:
            response = provider.charge(money=amount, credit_card=credit_card, options=options or {})
            return {
                "success": getattr(response, "success", False),
                "transaction_id": getattr(response, "transaction_id", None),
                "message": getattr(response, "message", ""),
                "response": str(response),
            }
        except Exception as e:
            logger.exception("Merchant charge failed via %s", self.provider_name)
            return {"success": False, "transaction_id": None, "message": str(e), "response": None}

    def authorize(self, amount: Decimal, credit_card: dict | None = None, options: dict | None = None) -> dict[str, Any]:
        provider = self._get_provider()
        try:
            response = provider.authorize(money=amount, credit_card=credit_card, options=options or {})
            return {"success": getattr(response, "success", False), "transaction_id": getattr(response, "transaction_id", None), "message": getattr(response, "message", "")}
        except Exception as e:
            logger.exception("Merchant authorize failed via %s", self.provider_name)
            return {"success": False, "message": str(e)}

    def capture(self, amount: Decimal, transaction_id: str, options: dict | None = None) -> dict[str, Any]:
        provider = self._get_provider()
        try:
            response = provider.capture(money=amount, identification=transaction_id, options=options or {})
            return {"success": getattr(response, "success", False), "transaction_id": getattr(response, "transaction_id", None), "message": getattr(response, "message", "")}
        except Exception as e:
            logger.exception("Merchant capture failed via %s", self.provider_name)
            return {"success": False, "message": str(e)}

    def refund(self, amount: Decimal, transaction_id: str, options: dict | None = None) -> dict[str, Any]:
        provider = self._get_provider()
        try:
            response = provider.refund(money=amount, identification=transaction_id, options=options or {})
            return {"success": getattr(response, "success", False), "transaction_id": getattr(response, "transaction_id", None), "message": getattr(response, "message", "")}
        except Exception as e:
            logger.exception("Merchant refund failed via %s", self.provider_name)
            return {"success": False, "message": str(e)}

    def recurring(self, amount: Decimal, credit_card: dict | None = None, options: dict | None = None) -> dict[str, Any]:
        provider = self._get_provider()
        try:
            response = provider.recurring(money=amount, credit_card=credit_card, options=options or {})
            return {"success": getattr(response, "success", False), "transaction_id": getattr(response, "transaction_id", None), "message": getattr(response, "message", "")}
        except Exception as e:
            logger.exception("Merchant recurring failed via %s", self.provider_name)
            return {"success": False, "message": str(e)}
