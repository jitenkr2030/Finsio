"""
Beancount synchronization with django-ledger.

Converts django-ledger JournalEntryModel entries to beancount
transaction format and writes them to the entity's beancount
file tree.
"""

from __future__ import annotations

import hashlib
import logging
import os
from datetime import datetime
from typing import Any
from uuid import UUID

from apps.core.models import Entity

logger = logging.getLogger(__name__)


class BeancountSync:
    """
    Synchronizes django-ledger journal entries to beancount files.

    For each journal entry in django-ledger:
      1. Look up account mappings (AccountMapping model)
      2. Generate a beancount transaction
      3. Write to the entity's transactions/ directory
      4. Record the sync state (BeancountSyncRecord)
    """

    def __init__(self, entity_id: UUID):
        self.entity = Entity.objects.get(id=entity_id)
        self.beancount_root = os.environ.get(
            "BEANCOUNT_PATH",
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "beancount"),
        )
        self.txn_dir = os.path.join(self.beancount_root, "transactions")
        os.makedirs(self.txn_dir, exist_ok=True)

    def sync_single_entry(self, journal_entry_id: UUID) -> dict[str, Any]:
        """Sync a single django-ledger journal entry to beancount."""
        from django_ledger.models.journal_entry import JournalEntryModel

        je = JournalEntryModel.objects.select_related("ledger").get(uuid=journal_entry_id)
        beancount_txn = self._convert_journal_entry(je)

        filename = f"{journal_entry_id}.beancount"
        filepath = os.path.join(self.txn_dir, filename)

        content = self._format_transaction(beancount_txn)
        with open(filepath, "w") as f:
            f.write(content)

        content_hash = hashlib.sha256(content.encode()).hexdigest()

        logger.info("Wrote beancount entry: %s", filepath)
        return {"file": filepath, "hash": content_hash}

    def sync_all(self) -> dict[str, Any]:
        """Re-sync all journal entries for this entity."""
        from django_ledger.models.journal_entry import JournalEntryModel

        entries = JournalEntryModel.objects.filter(
            ledger__entity=self.entity.ledger_entity_id,
        ).select_related("ledger")

        synced = 0
        failed = 0
        errors = []

        for je in entries:
            try:
                self.sync_single_entry(je.uuid)
                synced += 1
            except Exception as e:
                failed += 1
                errors.append({"journal_entry_id": str(je.uuid), "error": str(e)})
                logger.error("Failed to sync entry %s: %s", je.uuid, e)

        return {
            "entity": str(self.entity.id),
            "synced": synced,
            "failed": failed,
            "errors": errors,
        }

    def _convert_journal_entry(self, je) -> dict[str, Any]:
        """
        Convert a django-ledger JournalEntryModel to
        a beancount-serializable dict.
        """
        from apps.accounting.models import AccountMapping

        date = getattr(je, "timestamp", None) or getattr(je, "created_at", datetime.now())
        narration = getattr(je, "description", "") or str(je.uuid)
        entity_id = str(self.entity.id)

        # Get transaction lines from django-ledger
        postings = []
        try:
            transactions = je.transactionmodel_set.all()
            for txn in transactions:
                account_code = getattr(txn, "account_id", "unknown")
                amount = float(getattr(txn, "amount", 0) or 0)
                is_debit = getattr(txn, "tx_type", "") == "debit"

                # Map to beancount account name
                try:
                    mapping = AccountMapping.objects.get(
                        entity=self.entity,
                        ledger_account_code=account_code,
                    )
                    account_name = f"Assets:Ledger:{mapping.finsio_concept}"
                except AccountMapping.DoesNotExist:
                    account_name = f"Assets:Ledger:{account_code}"

                postings.append({
                    "account": account_name,
                    "amount": amount if is_debit else -amount,
                    "currency": "USD",
                })
        except Exception:
            postings = []

        return {
            "date": date.date() if hasattr(date, "date") else date,
            "flag": "*",
            "payee": self.entity.name,
            "narration": narration,
            "postings": postings,
            "metadata": {
                "entity": entity_id,
                "journal_entry_id": str(je.uuid),
            },
        }

    def _format_transaction(self, txn: dict) -> str:
        """Format a transaction dict as a beancount entry."""
        lines = []

        # Metadata
        for key, value in txn.get("metadata", {}).items():
            lines.append(f'  {key}: "{value}"')

        # Header
        date_str = txn["date"].strftime("%Y-%m-%d") if hasattr(txn["date"], "strftime") else str(txn["date"])
        lines.insert(0, f'{date_str} {txn["flag"]} "{txn["payee"]}" "{txn["narration"]}"')

        # Postings
        for p in txn.get("postings", []):
            amount = p["amount"]
            currency = p.get("currency", "USD")
            sign = "" if amount >= 0 else ""
            lines.append(f'  {p["account"]}  {sign}{amount:.2f} {currency}')

        return "\n".join(lines) + "\n"


class BeancountSyncService:
    """
    Service class for beancount synchronization.
    Used by invoicing and accounting services.
    """

    @staticmethod
    def sync_invoice(invoice):
        """Convert an invoice to beancount format."""
        from apps.accounting.beancount.generator import BeancountGenerator
        generator = BeancountGenerator(str(invoice.entity_id))
        return generator.generate_invoice_entry(invoice)

    @staticmethod
    def sync_payment(payment):
        """Convert a payment to beancount format."""
        from apps.accounting.beancount.generator import BeancountGenerator
        generator = BeancountGenerator(str(payment.invoice.entity_id))
        return generator.generate_payment_entry(payment)

    @staticmethod
    def get_sync_status(invoice_id):
        """Get sync status for an invoice."""
        from apps.accounting.models import BeancountSyncRecord
        records = BeancountSyncRecord.objects.filter(
            journal_entry_id=str(invoice_id),
        ).order_by("-created_at")
        if records.exists():
            return records.first().status
        return None

    @staticmethod
    def get_sync_stats():
        """Get overall sync statistics."""
        from apps.accounting.models import BeancountSyncRecord
        from django.db.models import Count
        return BeancountSyncRecord.objects.values("status").annotate(
            count=Count("id"),
        )
