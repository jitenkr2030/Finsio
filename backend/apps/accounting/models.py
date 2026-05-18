"""
Accounting models for Finsio.

Bridges our Invoice/Payment models with django-ledger's
double-entry accounting system (AccountModel, LedgerModel,
JournalEntryModel) and beancount's plaintext bookkeeping.

django-ledger API (verified):
  - django_ledger.models.entity: EntityModel, ChartOfAccountModel, BankAccountModel
  - django_ledger.models.ledger: LedgerModel
  - django_ledger.models.journal_entry: JournalEntryModel (via models.JournalEntryModel)
  - django_ledger.models.bill: BillModel
  - django_ledger.models: AccountModel
"""

from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class AccountMapping(TimeStampedModel):
    """
    Maps Finsio concepts to django-ledger accounts.

    When an invoice is created, we need to know which
    django-ledger AccountModel to debit/credit. This model
    stores those mappings per entity.
    """

    entity = models.ForeignKey(
        "core.Entity",
        on_delete=models.CASCADE,
        related_name="account_mappings",
    )
    finsio_concept = models.CharField(
        max_length=64,
        help_text="e.g. 'revenue', 'accounts_receivable', 'tax_collected'",
    )
    ledger_account_code = models.CharField(
        max_length=32,
        help_text="Account code in django-ledger's ChartOfAccounts",
    )
    ledger_account_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("entity", "finsio_concept")
        ordering = ["entity", "finsio_concept"]

    def __str__(self):
        return f"{self.entity.name}: {self.finsio_concept} -> {self.ledger_account_code}"


class BeancountSyncRecord(TimeStampedModel):
    """
    Tracks synchronization between django-ledger journal entries
    and beancount files.

    Every time a journal entry is created/updated in django-ledger,
    a corresponding beancount transaction is generated and this
    record tracks the sync state.
    """

    class SyncStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        SYNCED = "synced", "Synced"
        FAILED = "failed", "Failed"
        CONFLICT = "conflict", "Conflict"

    entity = models.ForeignKey(
        "core.Entity",
        on_delete=models.CASCADE,
        related_name="beancount_syncs",
    )
    journal_entry_id = models.CharField(
        max_length=64,
        help_text="UUID of the django-ledger JournalEntryModel",
    )
    ledger_account_code = models.CharField(
        max_length=32,
        blank=True,
        default="",
    )
    status = models.CharField(
        max_length=16,
        choices=SyncStatus.choices,
        default=SyncStatus.PENDING,
    )
    beancount_file = models.CharField(
        max_length=512,
        blank=True,
        default="",
        help_text="Path to the generated beancount file",
    )
    beancount_hash = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="SHA-256 of beancount content for conflict detection",
    )
    error_message = models.TextField(blank=True, default="")
    retry_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["entity", "status"]),
            models.Index(fields=["journal_entry_id"]),
        ]

    def __str__(self):
        return f"Sync {self.journal_entry_id[:8]}... [{self.status}]"

    def mark_synced(self, beancount_file: str, content_hash: str):
        self.status = self.SyncStatus.SYNCED
        self.beancount_file = beancount_file
        self.beancount_hash = content_hash
        self.error_message = ""
        self.save(update_fields=[
            "status", "beancount_file", "beancount_hash",
            "error_message", "updated_at",
        ])

    def mark_failed(self, error: str):
        self.status = self.SyncStatus.FAILED
        self.error_message = error
        self.retry_count += 1
        self.save(update_fields=[
            "status", "error_message", "retry_count", "updated_at",
        ])
