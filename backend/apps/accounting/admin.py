"""
Django admin configuration for accounting models.
"""

from django.contrib import admin

from .models import AccountMapping, BeancountSyncRecord


@admin.register(AccountMapping)
class AccountMappingAdmin(admin.ModelAdmin):
    list_display = [
        "entity",
        "finsio_concept",
        "ledger_account_code",
        "is_active",
    ]
    list_filter = ["entity", "is_active"]
    search_fields = ["finsio_concept", "ledger_account_code"]
    list_editable = ["is_active"]


@admin.register(BeancountSyncRecord)
class BeancountSyncRecordAdmin(admin.ModelAdmin):
    list_display = [
        "entity",
        "journal_entry_id",
        "status",
        "retry_count",
        "created_at",
    ]
    list_filter = ["entity", "status"]
    readonly_fields = [
        "journal_entry_id",
        "beancount_file",
        "beancount_hash",
        "error_message",
        "retry_count",
        "created_at",
        "updated_at",
    ]
    search_fields = ["journal_entry_id", "error_message"]
    date_hierarchy = "created_at"
