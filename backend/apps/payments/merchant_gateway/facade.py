"""
Merchant facade — unified billing interface for direct card charges.

Unlike getpaid-core (redirect flows) and django-payments (universal handling),
django-merchant supports direct server-side charges when you have card details.

This facade provides a single entry point for all merchant operations.

Usage:
    from apps.payments.merchant_gateway.facade import MerchantFacade

    facade = MerchantFacade()
    result = facade.charge("stripe", amount=Decimal("49.99"), card={...})
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from .providers import MerchantProviderWrapper

logger = logging.getLogger(__name__)

SUPPORTED_PROVIDERS = {"stripe", "paypal", "braintree", "authorize_net", "paymill", "wepay", "amazon"}


class MerchantFacade:
    """Unified facade over django-merchant's billing providers."""

    def __init__(self):
        self._providers: dict[str, MerchantProviderWrapper] = {}

    def _get_provider(self, name: str) -> MerchantProviderWrapper:
        name = name.lower().replace("-", "_")
        if name not in self._providers:
            if name not in SUPPORTED_PROVIDERS:
                raise ValueError(f"Unsupported merchant provider '{name}'. Available: {sorted(SUPPORTED_PROVIDERS)}")
            self._providers[name] = MerchantProviderWrapper(name)
        return self._providers[name]

    def charge(self, provider_name: str, amount: Decimal, credit_card: dict | None = None, options: dict | None = None) -> dict[str, Any]:
        """Directly charge a card via the specified provider."""
        provider = self._get_provider(provider_name)
        result = provider.charge(amount, credit_card, options)
        logger.info("Merchant charge via %s: %s — %s", provider_name, amount, "success" if result["success"] else "failed")
        return result

    def authorize(self, provider_name: str, amount: Decimal, credit_card: dict | None = None, options: dict | None = None) -> dict[str, Any]:
        """Authorize without capturing."""
        return self._get_provider(provider_name).authorize(amount, credit_card, options)

    def capture(self, provider_name: str, amount: Decimal, transaction_id: str, options: dict | None = None) -> dict[str, Any]:
        """Capture a previously authorized transaction."""
        return self._get_provider(provider_name).capture(amount, transaction_id, options)

    def refund(self, provider_name: str, amount: Decimal, transaction_id: str, options: dict | None = None) -> dict[str, Any]:
        """Refund a captured transaction."""
        return self._get_provider(provider_name).refund(amount, transaction_id, options)

    def recurring(self, provider_name: str, amount: Decimal, credit_card: dict | None = None, options: dict | None = None) -> dict[str, Any]:
        """Set up a recurring payment."""
        return self._get_provider(provider_name).recurring(amount, credit_card, options)

    def list_providers(self) -> list[str]:
        """List all supported merchant providers."""
        return sorted(SUPPORTED_PROVIDERS)
