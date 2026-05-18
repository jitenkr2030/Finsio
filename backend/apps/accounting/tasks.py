"""
Celery tasks for the accounting app.

Handles background beancount synchronization and reporting.
"""

from __future__ import annotations

import logging
from uuid import UUID

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_journal_entry_to_beancount(self, journal_entry_id: str, entity_id: str):
    """
    Sync a django-ledger JournalEntry to a beancount transaction.

    Generates the beancount entry, writes it to the entity's
    beancount directory, and records the sync state.
    """
    from apps.accounting.beancount.sync import BeancountSync
    from apps.accounting.models import BeancountSyncRecord

    sync_record, created = BeancountSyncRecord.objects.get_or_create(
        journal_entry_id=journal_entry_id,
        defaults={"entity_id": entity_id},
    )

    try:
        sync = BeancountSync(entity_id=UUID(entity_id))
        result = sync.sync_single_entry(UUID(journal_entry_id))

        sync_record.mark_synced(
            beancount_file=result.get("file", ""),
            content_hash=result.get("hash", ""),
        )
        logger.info("Synced journal entry %s to beancount", journal_entry_id[:8])
        return {"status": "synced", "journal_entry_id": journal_entry_id}

    except Exception as exc:
        sync_record.mark_failed(str(exc))
        logger.error("Failed to sync journal entry %s: %s", journal_entry_id[:8], exc)
        raise self.retry(exc=exc)


@shared_task(bind=True)
def bulk_sync_to_beancount(self, entity_id: str):
    """
    Full re-sync of all django-ledger journal entries to beancount.
    """
    from apps.accounting.beancount.sync import BeancountSync

    try:
        sync = BeancountSync(entity_id=UUID(entity_id))
        result = sync.sync_all()
        logger.info("Bulk sync complete for entity %s: %s", entity_id[:8], result)
        return result
    except Exception as exc:
        logger.error("Bulk sync failed for entity %s: %s", entity_id[:8], exc)
        raise


@shared_task
def generate_reports(entity_id: str):
    """
    Generate accounting reports for an entity.

    Uses django-ledger's EntityModel to produce:
    - Balance sheet
    - Profit & Loss
    - Cash flow statement
    """
    from apps.accounting.services.reporting_service import ReportingService

    service = ReportingService(entity_id=UUID(entity_id))
    reports = service.generate_all()
    logger.info("Reports generated for entity %s", entity_id[:8])
    return reports
