"""
Shared utility functions for Finsio.

Provides idempotency key generation, webhook signature
verification, and currency conversion helpers.
"""

import hashlib
import hmac
from decimal import Decimal, ROUND_HALF_UP
from typing import Any


# Zero-decimal currencies (amounts are already in smallest unit)
ZERO_DECIMAL_CURRENCIES = {"JPY", "KRW", "VND", "CLP", "BIF", "DJF", "GNF",
                            "ISK", "MGA", "PYG", "RWF", "UGX", "VUV", "XAF",
                            "XOF", "XPF"}


def generate_idempotency_key(*args: Any) -> str:
    """
    Generate a deterministic idempotency key from arbitrary arguments.

    Used to prevent duplicate payment creation when the same request
    is retried (e.g. network timeout, webhook replay).

    Example:
        key = generate_idempotency_key("49.99", "USD", "cust_001", "INV-001")
    """
    raw = "|".join(str(a) for a in args)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def verify_webhook_signature(
    payload: bytes,
    signature: str,
    secret: str,
    algorithm: str = "sha256",
) -> bool:
    """
    Verify an HMAC webhook signature from a payment provider.

    Args:
        payload:   Raw request body bytes
        signature: Signature from the provider's header
        secret:    Webhook signing secret
        algorithm: Hash algorithm (default sha256)

    Returns:
        True if the signature is valid
    """
    hash_func = getattr(hashlib, algorithm, None)
    if hash_func is None:
        return False

    expected = hmac.new(
        secret.encode("utf-8"),
        payload,
        hash_func,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


def to_minor_units(amount: Decimal, currency: str = "USD") -> int:
    """
    Convert a decimal amount to minor units (cents).

    Example:
        to_minor_units(Decimal("49.99"), "USD") → 4999
        to_minor_units(Decimal("1500"), "JPY")  → 1500
    """
    if currency.upper() in ZERO_DECIMAL_CURRENCIES:
        return int(amount)
    return int(
        (amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    )


def from_minor_units(amount: int, currency: str = "USD") -> Decimal:
    """
    Convert minor units back to a decimal amount.

    Example:
        from_minor_units(4999, "USD") → Decimal("49.99")
        from_minor_units(1500, "JPY") → Decimal("1500")
    """
    if currency.upper() in ZERO_DECIMAL_CURRENCIES:
        return Decimal(amount)
    return Decimal(amount) / 100


def mask_sensitive(value: str, visible: int = 4) -> str:
    """
    Mask a sensitive string, keeping only the last N characters visible.

    Example:
        mask_sensitive("sk_test_abc123def456") → "**********ef456"
    """
    if len(value) <= visible:
        return value
    return "*" * (len(value) - visible) + value[-visible:]
