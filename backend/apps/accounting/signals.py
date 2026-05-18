"""
Accounting signals.

Triggers beancount sync whenever a django-ledger JournalEntry
is created or updated.
"""

from __future__ import annotations

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


def _get_journal_entry_model():
    """Lazy import of JournalEntryModel to avoid circular imports."""
    try:
        from django_ledger.models.journal_entry import JournalEntryModel
        return JournalEntryModel
    except ImportError:
        return None


def connect_journal_entry_signals():
    """
    Connect post_save signal to django-ledger's JournalEntryModel.

    Called once at startup. We use lazy connection because
    django_ledger may not be installed in all environments.
    """
    JournalEntryModel = _get_journal_entry_model()
    if JournalEntryModel is None:
        logger.warning("django-ledger not available, skipping signal connection")
        return

    @receiver(post_save, sender=JournalEntryModel, dispatch_uid="sync_journal_to_beancount")
    def sync_journal_to_beancount(sender, instance, created, **kwargs):
        """Queue a beancount sync task when a journal entry changes."""
        try:
            from apps.accounting.tasks import sync_journal_entry_to_beancount
            sync_journal_entry_to_beancount.delay(
                journal_entry_id=str(instance.uuid),
                entity_id=str(getattr(instance.ledger, "entity_id", "")),
            )
            logger.debug(
                "Queued beancount sync for journal entry %s",
                instance.uuid,
            )
        except Exception as e:
            logger.error(
                "Failed to queue beancount sync for %s: %s",
                instance.uuid, e,
            )

    logger.info("Connected django-ledger journal entry signals")


# Connect on import
connect_journal_entry_signals()
