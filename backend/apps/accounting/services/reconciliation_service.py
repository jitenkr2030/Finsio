"""
Reconciliation service.

Compares django-ledger journal entries against beancount
transactions and reports discrepancies.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any
from uuid import UUID

from apps.core.models import Entity

logger = logging.getLogger(__name__)


def reconcile_entity(entity_id: UUID, dry_run: bool = True) -> dict[str, Any]:
    """
    Reconcile an entity's django-ledger data against beancount.

    Returns:
        dict with keys: matched, missing_in_beancount,
        missing_in_ledger, conflicts
    """
    entity = Entity.objects.get(id=entity_id)

    # Get journal entries from django-ledger
    try:
        from django_ledger.models.journal_entry import JournalEntryModel
        journal_entries = JournalEntryModel.objects.filter(
            ledger__entity=entity.ledger_entity_id,
        ).select_related("ledger")
    except Exception as e:
        logger.warning("Could not query django-ledger: %s", e)
        journal_entries = []

    # Get beancount transactions
    from apps.accounting.beancount.parser import BeancountParser

    parser = BeancountParser(entity.beancount_entity_name)
    beancount_txns = parser.get_transactions()

    # Build lookup maps
    ledger_map = {}
    for je in journal_entries:
        ref = getattr(je, "description", "") or str(je.uuid)
        ledger_map[ref] = je

    beancount_map = {}
    for txn in beancount_txns:
        ref = txn.get("narration", "")
        beancount_map[ref] = txn

    # Compare
    ledger_refs = set(ledger_map.keys())
    beancount_refs = set(beancount_map.keys())

    matched = ledger_refs & beancount_refs
    missing_in_beancount = ledger_refs - beancount_refs
    missing_in_ledger = beancount_refs - ledger_refs

    result = {
        "entity": str(entity.id),
        "entity_name": entity.name,
        "matched": len(matched),
        "missing_in_beancount": len(missing_in_beancount),
        "missing_in_ledger": len(missing_in_ledger),
        "conflicts": [],
        "dry_run": dry_run,
    }

    # Check content conflicts for matched entries
    for ref in matched:
        je = ledger_map[ref]
        txn = beancount_map[ref]

        je_amount = sum(
            float(getattr(t, "amount", 0))
            for t in getattr(je, "transactionmodel_set", []).all()
        ) if hasattr(je, "transactionmodel_set") else 0

        txn_amount = sum(
            float(p.get("units", {}).get("number", 0))
            for p in txn.get("postings", [])
        )

        if abs(je_amount - txn_amount) > 0.01:
            result["conflicts"].append({
                "reference": ref,
                "ledger_amount": je_amount,
                "beancount_amount": txn_amount,
                "difference": round(je_amount - txn_amount, 2),
            })

    logger.info(
        "Reconciliation for %s: %d matched, %d missing in beancount, "
        "%d missing in ledger, %d conflicts",
        entity.name,
        result["matched"],
        result["missing_in_beancount"],
        result["missing_in_ledger"],
        len(result["conflicts"]),
    )

    return result


class ReconciliationService:
    """Wrapper class for reconciliation functions used by views."""

    def __init__(self, entity_id=None):
        self.entity_id = entity_id

    def reconcile(self, entity_id=None, dry_run=True):
        return reconcile_entity(entity_id or self.entity_id, dry_run=dry_run)

    @staticmethod
    def quick_reconcile(entity_id, dry_run=True):
        return reconcile_entity(entity_id, dry_run=dry_run)
