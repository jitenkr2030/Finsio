"""
Shared choice constants used across Finsio models.
"""

from django.db import models


class Currency(models.TextChoices):
    """ISO 4217 currency codes supported by Finsio."""
    USD = "USD", "US Dollar"
    EUR = "EUR", "Euro"
    GBP = "GBP", "British Pound"
    JPY = "JPY", "Japanese Yen"
    CAD = "CAD", "Canadian Dollar"
    AUD = "AUD", "Australian Dollar"
    CHF = "CHF", "Swiss Franc"
    CNY = "CNY", "Chinese Yuan"
    SEK = "SEK", "Swedish Krona"
    NOK = "NOK", "Norwegian Krone"
    DKK = "DKK", "Danish Krone"
    NZD = "NZD", "New Zealand Dollar"


class PaymentStatus(models.TextChoices):
    """Canonical payment status values."""
    NEW = "new", "New"
    PREPARED = "prepared", "Prepared"
    IN_PROGRESS = "in_progress", "In Progress"
    PAID = "paid", "Paid"
    FAILED = "failed", "Failed"
    CANCELLED = "cancelled", "Cancelled"
    REFUNDED = "refunded", "Refunded"


class InvoiceStatus(models.TextChoices):
    """Canonical invoice status values."""
    DRAFT = "draft", "Draft"
    PENDING = "pending", "Pending Payment"
    PARTIAL = "partial", "Partially Paid"
    PAID = "paid", "Paid"
    OVERDUE = "overdue", "Overdue"
    CANCELLED = "cancelled", "Cancelled"


class ProcessorChoice(models.TextChoices):
    """Available payment processor identifiers."""
    STRIPE = "stripe", "Stripe"
    PAYPAL = "paypal", "PayPal"
    BRAINTREE = "braintree", "Braintree"
    AUTHORIZE_NET = "authorize_net", "Authorize.Net"
