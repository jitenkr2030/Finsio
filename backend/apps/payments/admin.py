"""
Django admin configuration for Payment models.

Provides rich admin views with inline event history,
filters, and search for operational support.
"""

from django.contrib import admin

from .models import Payment, PaymentEvent, PaymentMethod


class PaymentEventInline(admin.TabularInline):
    """Inline view of payment events in the payment detail page."""
    model = PaymentEvent
    extra = 0
    readonly_fields = [
        "event_type", "old_status", "new_status",
        "provider_event_id", "data", "created_at",
    ]
    ordering = ["-created_at"]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        "id", "status", "processor", "amount", "currency",
        "customer_id", "external_id", "paid_at", "created_at",
    ]
    list_filter = ["status", "processor", "currency", "created_at"]
    search_fields = [
        "customer_id", "customer_email", "external_id",
        "reference", "description",
    ]
    readonly_fields = [
        "id", "idempotency_key", "provider_metadata",
        "paid_at", "failed_at", "created_at", "updated_at",
    ]
    fieldsets = (
        ("Identity", {
            "fields": ("id", "status", "processor", "idempotency_key"),
        }),
        ("Financial", {
            "fields": ("amount", "currency", "amount_refunded"),
        }),
        ("Customer", {
            "fields": ("customer_id", "customer_email"),
        }),
        ("Provider", {
            "fields": ("external_id", "redirect_url", "callback_url", "provider_metadata"),
        }),
        ("Reference", {
            "fields": ("description", "reference", "invoice"),
        }),
        ("Timestamps", {
            "fields": ("paid_at", "failed_at", "created_at", "updated_at"),
        }),
    )
    inlines = [PaymentEventInline]
    date_hierarchy = "created_at"
    list_per_page = 50


@admin.register(PaymentEvent)
class PaymentEventAdmin(admin.ModelAdmin):
    list_display = [
        "id", "payment", "event_type", "old_status",
        "new_status", "provider_event_id", "created_at",
    ]
    list_filter = ["event_type", "created_at"]
    search_fields = ["payment__id", "provider_event_id"]
    readonly_fields = [
        "id", "payment", "event_type", "old_status",
        "new_status", "provider_event_id", "data", "created_at",
    ]
    date_hierarchy = "created_at"


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = [
        "customer_id", "provider", "display_name",
        "is_default", "created_at",
    ]
    list_filter = ["provider", "is_default"]
    search_fields = ["customer_id", "display_name", "external_token"]
    readonly_fields = ["id", "external_token", "metadata", "created_at", "updated_at"]
