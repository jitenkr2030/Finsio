"""
Serializers for the Invoicing app.
"""

from rest_framework import serializers

from .models import Invoice, InvoiceLineItem


class InvoiceLineItemSerializer(serializers.ModelSerializer):
    """Serializer for invoice line items."""
    line_total = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    tax_amount = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = InvoiceLineItem
        fields = [
            "id", "description", "quantity", "unit_price",
            "tax_rate", "category", "line_total", "tax_amount",
        ]


class InvoiceCreateSerializer(serializers.Serializer):
    """Validate input for invoice creation."""
    entity = serializers.CharField(max_length=100, default="default")
    customer = serializers.DictField()
    line_items = serializers.ListField(
        child=serializers.DictField(),
        min_length=1,
    )
    currency = serializers.CharField(max_length=3, default="USD")
    due_days = serializers.IntegerField(min_value=1, max_value=365, default=30)
    auto_collect = serializers.BooleanField(default=False)
    processor = serializers.CharField(max_length=30, required=False, allow_blank=True)
    notes = serializers.CharField(max_length=2000, required=False, default="")

    def validate_customer(self, value):
        if not value.get("email"):
            raise serializers.ValidationError("customer.email is required")
        if not value.get("name"):
            raise serializers.ValidationError("customer.name is required")
        return value

    def validate_line_items(self, value):
        for item in value:
            if not item.get("description"):
                raise serializers.ValidationError("Each line item must have a description")
            if not item.get("unit_price") and item.get("unit_price") != 0:
                raise serializers.ValidationError("Each line item must have a unit_price")
        return value


class InvoiceDetailSerializer(serializers.ModelSerializer):
    """Full invoice detail with line items."""
    line_items = InvoiceLineItemSerializer(many=True, read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id", "number", "status", "customer_name", "customer_email",
            "customer_id", "currency", "subtotal", "tax_amount", "total",
            "amount_paid", "amount_due", "issue_date", "due_date", "paid_at",
            "payment_url", "notes", "line_items", "created_at",
        ]


class InvoiceListSerializer(serializers.ModelSerializer):
    """Compact serializer for invoice list responses."""

    class Meta:
        model = Invoice
        fields = [
            "id", "number", "status", "customer_name", "currency",
            "total", "amount_due", "issue_date", "due_date", "paid_at",
        ]
