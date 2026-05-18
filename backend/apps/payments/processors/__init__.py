"""
Payment processor implementations.

Each processor bridges:
  - python-getpaid-core's BaseProcessor interface
  - django-payments' provider gateway (where applicable)
  - The provider's native SDK for direct API calls
"""

from .authorize_net_processor import AuthorizeNetProcessor
from .braintree_processor import BraintreeProcessor
from .paypal_processor import PayPalProcessor
from .stripe_processor import StripeProcessor

__all__ = [
    "StripeProcessor",
    "PayPalProcessor",
    "BraintreeProcessor",
    "AuthorizeNetProcessor",
]
