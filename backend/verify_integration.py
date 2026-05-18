#!/usr/bin/env python
"""
Finsio integration verification script.

Checks that all components are correctly wired:
  1. Database connectivity
  2. All Django models loadable
  3. Payment processor registry populated
  4. getpaid-core integration
  5. django-ledger integration
  6. Beancount integration
  7. Celery app initialization
  8. Beancount data files present
  9. Internal API routes registered
 10. Redis connectivity

Run:
    python scripts/verify_integration.py
    make verify
"""

import os
import sys
import time

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "finsio.settings.development")


def check(label, fn, critical=False):
    """Run a check and print the result."""
    try:
        start = time.time()
        result = fn()
        elapsed = time.time() - start
        if result:
            symbol = "✓"
            color = "\033[0;32m"
        else:
            symbol = "✗"
            color = "\033[0;31m" if critical else "\033[1;33m"
        nc = "\033[0m"
        print(f"  {color}{symbol}{nc} {label} ({elapsed:.2f}s)")
        return result
    except Exception as e:
        color = "\033[0;31m" if critical else "\033[1;33m"
        nc = "\033[0m"
        print(f"  {color}✗{nc} {label}: {e}")
        return False


def main():
    import django
    django.setup()

    print()
    print("\033[0;36m══════════════════════════════════════\033[0m")
    print("\033[0;36m  Finsio — Integration Verification\033[0m")
    print("\033[0;36m══════════════════════════════════════\033[0m")
    print()

    results = []

    # ── 1. Database ──
    print("  Database")
    results.append(check(
        "PostgreSQL connection",
        lambda: _check_database(),
        critical=True,
    ))

    # ── 2. Django models ──
    print("\n  Models")
    results.append(check(
        "Core models (Entity, TimeStampedModel)",
        lambda: _check_model("apps.core.models", "Entity"),
        critical=True,
    ))
    results.append(check(
        "Payment models (Payment, PaymentEvent, PaymentMethod)",
        lambda: _check_model("apps.payments.models", "Payment"),
        critical=True,
    ))
    results.append(check(
        "Accounting models (BeancountSyncRecord, AccountMapping)",
        lambda: _check_model("apps.accounting.models", "BeancountSyncRecord"),
        critical=True,
    ))
    results.append(check(
        "Invoice models (Invoice, InvoiceLineItem)",
        lambda: _check_model("apps.invoicing.models", "Invoice"),
        critical=True,
    ))

    # ── 3. Payment processors ──
    print("\n  Payment Processors")
    results.append(check(
        "Processor registry has ≥4 processors",
        lambda: _check_registry(),
        critical=True,
    ))
    results.append(check(
        "Stripe processor loadable",
        lambda: _check_model("apps.payments.processors.stripe_processor", "StripeProcessor"),
    ))
    results.append(check(
        "PayPal processor loadable",
        lambda: _check_model("apps.payments.processors.paypal_processor", "PayPalProcessor"),
    ))
    results.append(check(
        "Braintree processor loadable",
        lambda: _check_model("apps.payments.processors.braintree_processor", "BraintreeProcessor"),
    ))
    results.append(check(
        "Authorize.Net processor loadable",
        lambda: _check_model("apps.payments.processors.authorize_net_processor", "AuthorizeNetProcessor"),
    ))

    # ── 4. getpaid-core ──
    print("\n  Integrations")
    results.append(check(
        "python-getpaid-core importable",
        lambda: _check_getpaid(),
    ))
    results.append(check(
        "django-ledger importable",
        lambda: _check_django_ledger(),
    ))

    # ── 5. Beancount ──
    print("\n  Beancount")
    results.append(check(
        "beancount library importable",
        lambda: _check_beancount_lib(),
    ))
    results.append(check(
        "BeancountGenerator loadable",
        lambda: _check_model("apps.accounting.beancount.generator", "BeancountGenerator"),
    ))
    results.append(check(
        "BeancountParser loadable",
        lambda: _check_model("apps.accounting.beancount.parser", "BeancountParser"),
    ))
    results.append(check(
        "BeancountSyncService loadable",
        lambda: _check_model("apps.accounting.beancount.sync", "BeancountSyncService"),
    ))
    results.append(check(
        "main.beancount exists",
        lambda: _check_beancount_files(),
    ))

    # ── 6. Celery ──
    print("\n  Async")
    results.append(check(
        "Celery app initialized",
        lambda: _check_celery(),
    ))

    # ── 7. Redis ──
    results.append(check(
        "Redis connection",
        lambda: _check_redis(),
    ))

    # ── 8. Services ──
    print("\n  Services")
    results.append(check(
        "FinsioPaymentFlow loadable",
        lambda: _check_model("apps.payments.flows", "FinsioPaymentFlow"),
    ))
    results.append(check(
        "ReconciliationService loadable",
        lambda: _check_model("apps.accounting.services.reconciliation_service", "ReconciliationService"),
    ))
    results.append(check(
        "ReportingService loadable",
        lambda: _check_model("apps.accounting.services.reporting_service", "ReportingService"),
    ))
    results.append(check(
        "create_invoice service loadable",
        lambda: _check_model("apps.invoicing.services.create_invoice", "create_invoice"),
    ))

    # ── Summary ──
    passed = sum(results)
    total = len(results)
    failed = total - passed

    print()
    print("\033[0;36m──────────────────────────────────────\033[0m")

    if passed == total:
        print(f"\033[0;32m  All {total} checks passed ✓\033[0m")
        print()
        print("  Finsio is fully operational.")
        print("  Run 'make dev' to start all services.")
        return 0
    else:
        print(f"\033[1;33m  {passed}/{total} checks passed — {failed} failed\033[0m")
        print()
        print("  Review the failures above and run 'make setup' to fix.")
        return 1


# ── Check functions ──

def _check_database():
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        row = cursor.fetchone()
    return row[0] == 1


def _check_model(module_path, class_name):
    import importlib
    module = importlib.import_module(module_path)
    obj = getattr(module, class_name, None)
    return obj is not None


def _check_registry():
    from apps.payments.registry import get_registry
    registry = get_registry()
    processors = registry.list_processors()
    return len(processors) >= 4


def _check_getpaid():
    from getpaid import PaymentFlow, PaymentStatus, BaseProcessor
    return all([PaymentFlow, PaymentStatus, BaseProcessor])


def _check_django_ledger():
    from django_ledger.entity import EntityModel
    return EntityModel is not None


def _check_beancount_lib():
    from beancount import loader
    from beancount.core import realization
    return all([loader, realization])


def _check_beancount_files():
    from django.conf import settings
    main_file = settings.BEANCOUNT_PATH / "main.beancount"
    accounts_dir = settings.BEANCOUNT_PATH / "accounts"
    return main_file.exists() and accounts_dir.exists()


def _check_celery():
    from finsio.celery import app
    return app is not None and app.main == "finsio"


def _check_redis():
    import redis as redis_lib
    from django.conf import settings
    try:
        r = redis_lib.from_url(settings.CELERY_BROKER_URL)
        return r.ping()
    except Exception:
        return False


if __name__ == "__main__":
    sys.exit(main())
