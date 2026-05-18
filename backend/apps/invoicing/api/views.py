"""
Invoice API views for Finsio.

Provides invoice creation, listing, and detail retrieval.
Invoice creation triggers:
  1. Line item storage
  2. Total calculation
  3. Beancount accounting entry
  4. Optional payment link generation
"""

import logging

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from ..models import Invoice
from ..serializers import (
    InvoiceCreateSerializer,
    InvoiceDetailSerializer,
    InvoiceListSerializer,
)
from ..services.create_invoice import create_invoice
from ..services.collect_payment import get_invoice_payment_status

logger = logging.getLogger(__name__)


@api_view(["POST"])
def invoice_create(request: Request) -> Response:
    """
    POST /internal/invoicing/invoices/create

    Creates an invoice with line items, posts accounting
    entries, and optionally generates a payment link.
    """
    serializer = InvoiceCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"error": "validation_error", "details": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    data = serializer.validated_data

    try:
        invoice = create_invoice(
            entity_slug=data.get("entity", "default"),
            customer=data["customer"],
            line_items=data["line_items"],
            currency=data.get("currency", "USD"),
            due_days=int(data.get("due_days", 30)),
            auto_collect=data.get("auto_collect", False),
            processor=data.get("processor"),
            notes=data.get("notes", ""),
            created_by=request.user if request.user.is_authenticated else None,
        )
    except Exception as e:
        logger.exception("Invoice creation failed")
        return Response(
            {"error": "invoice_creation_failed", "detail": str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response({
        "invoice_id": str(invoice.id),
        "number": invoice.number,
        "status": invoice.status,
        "total": str(invoice.total),
        "currency": invoice.currency,
        "payment_url": invoice.payment_url,
        "due_date": invoice.due_date.isoformat(),
    }, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def invoice_list(request: Request) -> Response:
    """
    GET /internal/invoicing/invoices

    List invoices with optional filters.
    """
    queryset = Invoice.objects.all()

    status_filter = request.query_params.get("status")
    if status_filter:
        queryset = queryset.filter(status=status_filter)

    entity = request.query_params.get("entity")
    if entity:
        queryset = queryset.filter(entity__slug=entity)

    customer = request.query_params.get("customer_id")
    if customer:
        queryset = queryset.filter(customer_id=customer)

    page = max(int(request.query_params.get("page", 1)), 1)
    page_size = min(int(request.query_params.get("page_size", 50)), 200)
    offset = (page - 1) * page_size

    total = queryset.count()
    invoices = queryset[offset:offset + page_size]

    serializer = InvoiceListSerializer(invoices, many=True)

    return Response({
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if page_size > 0 else 0,
        "results": serializer.data,
    })


@api_view(["GET"])
def invoice_detail(request: Request, invoice_id: str) -> Response:
    """
    GET /internal/invoicing/invoices/{invoice_id}

    Retrieve full invoice details including line items
    and payment status.
    """
    try:
        invoice = Invoice.objects.get(id=invoice_id)
    except Invoice.DoesNotExist:
        return Response(
            {"error": "not_found", "message": f"Invoice {invoice_id} not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = InvoiceDetailSerializer(invoice)
    payment_status = get_invoice_payment_status(invoice)

    return Response({
        **serializer.data,
        "payment_summary": payment_status,
    })
