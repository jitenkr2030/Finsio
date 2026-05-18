"""
Custom exceptions and DRF exception handler for Finsio.

Provides domain-specific exception classes and a custom
handler that formats all errors consistently as JSON.
"""

import logging

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Domain exceptions
# ──────────────────────────────────────────────

class PaymentProviderError(APIException):
    """The external payment provider returned an error."""
    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = "Payment provider returned an error."
    default_code = "payment_provider_error"


class InsufficientDataError(APIException):
    """Required data is missing from the request."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Required data is missing."
    default_code = "insufficient_data"


class ReconciliationError(APIException):
    """Ledger reconciliation detected a discrepancy."""
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Ledger reconciliation failed."
    default_code = "reconciliation_error"


class BeancountSyncError(APIException):
    """Failed to sync data to the beancount audit file."""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "Beancount synchronization failed."
    default_code = "beancount_sync_error"


class EntityNotFoundError(APIException):
    """The requested business entity does not exist."""
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Entity not found."
    default_code = "entity_not_found"


class ProcessorNotAvailableError(APIException):
    """No payment processor available for the request."""
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "No suitable payment processor available."
    default_code = "processor_not_available"


class DuplicateTransactionError(APIException):
    """An idempotent request that has already been processed."""
    status_code = status.HTTP_409_CONFLICT
    default_detail = "This transaction has already been processed."
    default_code = "duplicate_transaction"


# ──────────────────────────────────────────────
# Custom DRF exception handler
# ──────────────────────────────────────────────

def custom_exception_handler(exc, context):
    """
    Wraps DRF's default exception handler to produce a
    consistent error envelope:

    {
        "error": "<error_code>",
        "message": "<human-readable message>",
        "details": { ... }   // optional field-level errors
    }
    """
    response = exception_handler(exc, context)

    if response is not None:
        error_code = getattr(exc, "default_code", "error")

        if isinstance(response.data, dict):
            # Preserve detail and code from DRF
            error_data = {
                "error": error_code,
                "message": response.data.get("detail", str(response.data)),
            }
            # Include field-level errors if present
            field_errors = {
                k: v for k, v in response.data.items() if k != "detail"
            }
            if field_errors:
                error_data["details"] = field_errors
        elif isinstance(response.data, list):
            error_data = {
                "error": error_code,
                "message": "; ".join(str(item) for item in response.data),
            }
        else:
            error_data = {
                "error": error_code,
                "message": str(response.data),
            }

        response.data = error_data

    return response
