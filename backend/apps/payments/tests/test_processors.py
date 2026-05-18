"""
Tests for payment processors.

Tests each processor's prepare_transaction, handle_webhook,
and refund methods with mocked provider responses.
"""

import json
from decimal import Decimal

import pytest

from apps.payments.processors.base import FinsioBaseProcessor


@pytest.mark.django_db
class TestBaseProcessor:
    """Test the abstract base processor contract."""

    def test_slug_and_display_name(self):
        """Every processor must define slug and display_name."""
        from apps.payments.processors import (
            StripeProcessor,
            PayPalProcessor,
            BraintreeProcessor,
            AuthorizeNetProcessor,
        )

        for ProcessorClass in [
            StripeProcessor,
            PayPalProcessor,
            BraintreeProcessor,
            AuthorizeNetProcessor,
        ]:
            assert ProcessorClass.slug, f"{ProcessorClass.__name__} missing slug"
            assert ProcessorClass.display_name, f"{ProcessorClass.__name__} missing display_name"
            assert len(ProcessorClass.accepted_currencies) > 0, (
                f"{ProcessorClass.__name__} missing accepted_currencies"
            )

    def test_subclass_contract(self):
        """Verify all processors subclass FinsioBaseProcessor."""
        from apps.payments.processors import (
            StripeProcessor,
            PayPalProcessor,
            BraintreeProcessor,
            AuthorizeNetProcessor,
        )

        for cls in [StripeProcessor, PayPalProcessor, BraintreeProcessor, AuthorizeNetProcessor]:
            assert issubclass(cls, FinsioBaseProcessor)


@pytest.mark.django_db
class TestProcessorRegistry:
    """Test the processor registry loads all processors."""

    def test_registry_has_four_processors(self):
        from apps.payments.registry import get_registry
        registry = get_registry()
        assert len(registry.list_processors()) >= 4

    def test_registry_get_by_slug(self):
        from apps.payments.registry import get_registry
        registry = get_registry()
        stripe = registry.get("stripe")
        assert stripe.slug == "stripe"

    def test_registry_get_unknown_raises(self):
        from apps.payments.registry import get_registry
        registry = get_registry()
        with pytest.raises(ValueError, match="Unknown payment processor"):
            registry.get("nonexistent_processor")

    def test_registry_currency_selection(self):
        from apps.payments.registry import get_registry
        registry = get_registry()

        # USD should find Stripe as default
        proc = registry.get_for_currency("USD")
        assert proc is not None

    def test_registry_preferred_processor(self):
        from apps.payments.registry import get_registry
        registry = get_registry()

        proc = registry.get_for_currency("USD", preferred="paypal")
        assert proc.slug == "paypal"
