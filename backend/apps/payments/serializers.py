"""
Serializers for the Payments app.

Provides input validation and output formatting for
payment API endpoints.
"""

from decimal import Decimal

from rest_framework import serializers

from apps.core.choices import Currency, PaymentStatus, ProcessorChoice

from .models import Payment, PaymentEvent, PaymentMethod


class PaymentPrepareSerializer(serializers.Serializer):
    """Validate input for POST /payments/prepare."""
    amount = serializers.DecimalField(
        max_digits=14, decimal_places=2, min_value=Decimal("0.01"),
    )
    currency = serializers.ChoiceField(
        choices=Currency.choices, default="USD",
    )
    processor = serializers.ChoiceField(
        choices=ProcessorChoice.choices, required=False, allow_null=True,
    )
    customer = serializers.DictField(
        child=serializers.CharField(allow_blank=True),
    )
    description = serializers.CharField(
        max_length=500, required=False, default="",
    )
    reference = serializers.CharField(
        max_length=255, required=False, default="",
    )
    callback_url = serializers.URLField(required=False, allow_null=True)
    created_by = serializers.IntegerField(required=False, allow_null=True)

    def validate_customer(self, value):
        if not value.get("id"):
            raise serializers.ValidationError("customer.id is required")
        if not value.get("email"):
            raise serializers.ValidationError("customer.email is required")
        return value


class PaymentStatusSerializer(serializers.Serializer):
    """Output serializer for payment status queries."""
    payment_id = serializers.UUIDField(source="id")
    status = serializers.CharField()
    processor = serializers.CharField(allow_null=True)
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    currency = serializers.CharField()
    external_id = serializers.CharField(allow_null=True)
    redirect_url = serializers.URLField(allow_null=True)
    customer_id = serializers.CharField(allow_null=True)
    customer_email = serializers.EmailField(allow_null=True)
    description = serializers.CharField()
    reference = serializers.CharField()
    paid_at = serializers.DateTimeField(allow_null=True)
    failed_at = serializers.DateTimeField(allow_null=True)
    created_at = serializers.DateTimeField()


class PaymentListSerializer(serializers.ModelSerializer):
    """Compact serializer for payment list responses."""
    class Meta:
        model = Payment
        fields = [
            "id", "status", "processor", "amount", "currency",
            "customer_id", "reference", "paid_at", "created_at",
        ]


class PaymentEventSerializer(serializers.ModelSerializer):
    """Serializer for payment audit events."""
    class Meta:
        model = PaymentEvent
        fields = [
            "id", "event_type", "old_status", "new_status",
            "provider_event_id", "data", "created_at",
        ]


class PaymentMethodSerializer(serializers.ModelSerializer):
    """Serializer for saved payment methods."""
    class Meta:
        model = PaymentMethod
        fields = [
            "id", "customer_id", "provider", "display_name",
            "is_default", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ProcessorListSerializer(serializers.Serializer):
    """Serializer for listing available processors."""
    slug = serializers.CharField()
    name = serializers.CharField()
    currencies = serializers.ListField(child=serializers.CharField())
