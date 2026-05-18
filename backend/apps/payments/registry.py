"""
Payment processor registry for Finsio.

Unifies processors from three sources:
  1. getpaid-core entry points (pyproject.toml [project.entry-points])
  2. Direct processor class registration
  3. Fallback to django-payments / django-merchant providers

The singleton `processor_registry` is the single point of
truth for all available payment processors.
"""

from __future__ import annotations

import logging
from functools import lru_cache

logger = logging.getLogger(__name__)


class ProcessorRegistry:
    """
    Unified registry of all available payment processors.

    Usage:
        registry = get_registry()
        processor = registry.get("stripe")
        result = await processor.prepare_transaction(...)
    """

    def __init__(self):
        self._processors: dict[str, type] = {}

    def register(self, slug: str, processor_class: type):
        """Register a processor class under a slug identifier."""
        self._processors[slug] = processor_class
        logger.info(
            "Registered payment processor: %s (%s)",
            slug, processor_class.__name__,
        )

    def get(self, slug: str):
        """
        Retrieve a processor instance by slug.

        Raises ValueError if the slug is not registered.
        """
        if slug not in self._processors:
            available = ", ".join(sorted(self._processors.keys()))
            raise ValueError(
                f"Unknown payment processor '{slug}'. "
                f"Available: [{available}]"
            )
        return self._processors[slug]()

    def get_for_currency(self, currency: str, preferred: str | None = None):
        """
        Find the best processor for a given currency.

        If a preferred processor is specified and supports the
        currency, it is returned. Otherwise, the first matching
        processor is returned.

        Raises ValueError if no processor supports the currency.
        """
        # Try preferred first
        if preferred and preferred in self._processors:
            proc = self._processors[preferred]()
            if currency.upper() in [c.upper() for c in proc.accepted_currencies]:
                return proc

        # Find any matching processor
        for slug, cls in self._processors.items():
            proc = cls()
            if currency.upper() in [c.upper() for c in proc.accepted_currencies]:
                return proc

        raise ValueError(
            f"No payment processor available for currency {currency}. "
            f"Registered: {list(self._processors.keys())}"
        )

    def list_processors(self) -> list[dict]:
        """Return metadata for all registered processors."""
        result = []
        for slug, cls in self._processors.items():
            instance = cls()
            result.append({
                "slug": slug,
                "name": getattr(cls, "display_name", slug),
                "currencies": getattr(instance, "accepted_currencies", []),
            })
        return result

    @property
    def available_slugs(self) -> list[str]:
        """List of all registered processor slugs."""
        return list(self._processors.keys())


# ──────────────────────────────────────────────
# Singleton instance
# ──────────────────────────────────────────────
processor_registry = ProcessorRegistry()


@lru_cache(maxsize=1)
def get_registry() -> ProcessorRegistry:
    """
    Returns the populated processor registry.

    On first call, loads all built-in processors.
    Subsequent calls return the cached instance.
    """
    if not processor_registry._processors:
        _load_builtin_processors(processor_registry)
    return processor_registry


def _load_builtin_processors(reg: ProcessorRegistry):
    """Load the built-in processor implementations."""
    from .processors.stripe_processor import StripeProcessor
    from .processors.paypal_processor import PayPalProcessor
    from .processors.braintree_processor import BraintreeProcessor
    from .processors.authorize_net_processor import AuthorizeNetProcessor

    reg.register("stripe", StripeProcessor)
    reg.register("paypal", PayPalProcessor)
    reg.register("braintree", BraintreeProcessor)
    reg.register("authorize_net", AuthorizeNetProcessor)
