#!/usr/bin/env python
"""
Export all historical Finsio data to beancount files.

Scans invoices, payments, and refund records and generates
.beancount entries for any that haven't been synced yet.
Uses the BeancountSyncRecord model to ensure exactly-once
export semantics.

Run:
    python scripts/export_beancount.py
    make export-bc
"""

import os
import sys
from datetime import date

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "finsio.settings.development")


def export():
    """Main export function."""
    import django
    django.setup()

    from apps.core.models import Entity
    from apps.accounting.beancount.sync import BeancountSyncService
    from apps.accounting.models import BeancountSyncRecord
    from apps.invoicing.models import Invoice
    from apps.payments.models import Payment

    print("=" * 50)
    print("  Finsio — Beancount Export")
    print("=" * 50)
    print()

    # Show current sync stats before export
    stats_before = BeancountSyncService.get_sync_stats()
    print("  Current sync status:")
    for obj_type, count in stats_before.items():
        print(f"    {obj_type}: {count} records synced")
    print()

    total_synced = 0
    total_skipped = 0
    total_errors = 0

    for entity in Entity.objects.filter(is_active=True):
        print(f"  Entity: {entity.name} ({entity.slug})")

        # ── Export invoices ──
        invoices = Invoice.objects.filter(entity=entity).order_by("issue_date")
        for invoice in invoices:
            already_synced = BeancountSyncService.get_sync_status(
                BeancountSyncRecord.ObjectType.INVOICE,
                invoice.pk,
            )
            if already_synced:
                total_skipped += 1
                continue

            try:
                text = BeancountSyncService.sync_invoice(invoice)
                if text:
                    print(f"    ✓ Invoice {invoice.number} → beancount")
                    total_synced += 1
                else:
                    total_skipped += 1
            except Exception as e:
                print(f"    ✗ Invoice {invoice.number}: {e}")
                total_errors += 1

        # ── Export payments ──
        payments = Payment.objects.filter(
            invoice__entity=entity,
            status="paid",
        ).order_by("paid_at")

        for payment in payments:
            already_synced = BeancountSyncService.get_sync_status(
                BeancountSyncRecord.ObjectType.PAYMENT,
                payment.pk,
            )
            if already_synced:
                total_skipped += 1
                continue

            try:
                text = BeancountSyncService.sync_payment(payment)
                if text:
                    print(f"    ✓ Payment {str(payment.id)[:12]}... → beancount")
                    total_synced += 1
                else:
                    total_skipped += 1
            except Exception as e:
                print(f"    ✗ Payment {str(payment.id)[:12]}...: {e}")
                total_errors += 1

        # ── Export refunds ──
        refunds = Payment.objects.filter(
            invoice__entity=entity,
            status="refunded",
        ).order_by("updated_at")

        for refund in refunds:
            try:
                text = BeancountSyncService.sync_refund(refund)
                if text:
                    print(f"    ✓ Refund for {str(refund.id)[:12]}... → beancount")
                    total_synced += 1
            except Exception as e:
                print(f"    ✗ Refund {str(refund.id)[:12]}...: {e}")
                total_errors += 1

    # ── Summary ──
    print()
    print("=" * 50)
    print(f"  Synced:   {total_synced} new records")
    print(f"  Skipped:  {total_skipped} (already synced)")
    print(f"  Errors:   {total_errors}")
    print()

    # Show final stats
    stats_after = BeancountSyncService.get_sync_stats()
    print("  Updated sync status:")
    for obj_type, count in stats_after.items():
        print(f"    {obj_type}: {count} records")
    print()

    # Validate the beancount files
    from apps.accounting.beancount.parser import BeancountParser
    parser = BeancountParser()
    validation = parser.validate()

    print("  Beancount validation:")
    print(f"    Entries:  {validation['entries_count']}")
    print(f"    Accounts: {validation['accounts_count']}")
    print(f"    Errors:   {validation['errors_count']}")
    if validation["errors"]:
        print("    First errors:")
        for err in validation["errors"][:5]:
            print(f"      - {err.get('message', 'unknown')}")

    status = "passed ✓" if validation["valid"] else "FAILED ✗"
    print(f"    Status:   {status}")

    print()
    print(f"  Files written to: beancount/transactions/")
    print("=" * 50)
    print("  Export complete.")


if __name__ == "__main__":
    export()
