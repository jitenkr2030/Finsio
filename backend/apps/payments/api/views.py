"""
Payment API views for Finsio.

These endpoints are called by the Fusio gateway on behalf
of external clients. They live under /internal/payments/.
"""

import logging

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from apps.core.choices import PaymentStatus
from apps.core.utils import generate_idempotency_key

from ..flows import FinsioPaymentFlow
from ..models import Payment
from ..registry import get_registry
from ..serializers import (
    PaymentListSerializer,
    PaymentPrepareSerializer,
    PaymentStatusSerializer,
    ProcessorListSerializer,
)

logger = logging.getLogger(__name__)


@api_view(["POST"])
def prepare_payment(request: Request) -> Response:
    """
    POST /internal/payments/prepare

    Creates a payment record and prepares it with the requested
    (or auto-selected) payment processor.

    Idempotent: if an identical request is retried, the existing
    payment is returned instead of creating a duplicate.
    """
    serializer = PaymentPrepareSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"error": "validation_error", "details": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    data = serializer.validated_data
    customer = data["customer"]
    amount = data["amount"]
    currency = data["currency"]
    processor_slug = data.get("processor")

    registry = get_registry()

    # Auto-select processor if not specified
    if not processor_slug:
        try:
            processor = registry.get_for_currency(currency)
            processor_slug = processor.slug
        except ValueError as e:
            return Response(
                {"error": "processor_not_available", "message": str(e)},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
    else:
        try:
            registry.get(processor_slug)
        except ValueError as e:
            return Response(
                {"error": "invalid_processor", "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    # Generate idempotency key from request content
    idem_key = generate_idempotency_key(
        amount, currency, customer["id"], data.get("reference", ""),
    )

    # Create or retrieve (idempotent)
    payment, created = Payment.objects.get_or_create(
        idempotency_key=idem_key,
        defaults={
            "amount": amount,
            "currency": currency,
            "description": data.get("description", ""),
            "reference": data.get("reference", ""),
            "customer_id": customer["id"],
            "customer_email": customer.get("email"),
            "callback_url": data.get("callback_url"),
            "status": PaymentStatus.NEW,
            "created_by_id": data.get("created_by"),
        },
    )

    # If payment already exists and is in a terminal state, return it
    if not created and payment.is_terminal:
        return Response({
            "payment_id": str(payment.id),
            "status": payment.status,
            "processor": payment.processor,
            "redirect_url": payment.redirect_url,
            "external_id": payment.external_id,
            "message": "Payment already processed",
        })

    # Prepare the transaction with the processor
    flow = FinsioPaymentFlow()
    try:
        result = flow.prepare(payment, processor_slug)
    except Exception as e:
        logger.exception("Payment preparation failed for %s", payment.id)
        payment.mark_failed(str(e))
        return Response(
            {
                "error": "payment_preparation_failed",
                "payment_id": str(payment.id),
                "detail": str(e),
            },
            status=status.HTTP_502_BAD_GATEWAY,
        )

    return Response({
        "payment_id": str(payment.id),
        "status": payment.status,
        "processor": processor_slug,
        "redirect_url": result.get("redirect_url"),
        "extra_data": result.get("data", {}),
    }, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def payment_status(request: Request, payment_id: str) -> Response:
    """
    GET /internal/payments/{payment_id}

    Returns the current status and details of a payment.
    """
    try:
        payment = Payment.objects.get(id=payment_id)
    except Payment.DoesNotExist:
        return Response(
            {"error": "not_found", "message": f"Payment {payment_id} not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = PaymentStatusSerializer(payment)
    return Response(serializer.data)


@api_view(["GET"])
def payment_list(request: Request) -> Response:
    """
    GET /internal/payments/

    List payments with optional filters: status, customer_id,
    processor, page, page_size.
    """
    queryset = Payment.objects.all()

    # Apply filters
    status_filter = request.query_params.get("status")
    if status_filter:
        queryset = queryset.filter(status=status_filter)

    customer = request.query_params.get("customer_id")
    if customer:
        queryset = queryset.filter(customer_id=customer)

    processor = request.query_params.get("processor")
    if processor:
        queryset = queryset.filter(processor=processor)

    # Pagination
    page_size = min(int(request.query_params.get("page_size", 50)), 200)
    page = max(int(request.query_params.get("page", 1)), 1)
    offset = (page - 1) * page_size

    total = queryset.count()
    payments = queryset[offset:offset + page_size]

    serializer = PaymentListSerializer(payments, many=True)

    return Response({
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if page_size > 0 else 0,
        "results": serializer.data,
    })


@api_view(["GET"])
def list_processors(request: Request) -> Response:
    """
    GET /internal/payments/processors

    List all available payment processors and their
    supported currencies.
    """
    registry = get_registry()
    serializer = ProcessorListSerializer(registry.list_processors(), many=True)
    return Response({"processors": serializer.data})
