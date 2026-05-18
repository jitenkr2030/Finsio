#!/usr/bin/env python
"""
Seed the Finsio database with sample development data.

Creates:
  - A sample business entity
  - Chart of accounts (via django-ledger)
  - Sample invoices with line items
  - Sample payments in various states
  - Beancount account mappings

Run:
    python scripts/seed_data.py
    make seed
"""

import os
import sys
from datetime import date, timedelta
from decimal import Decimal

# Ensure Django settings are loaded
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "finsio.settings.development")


def seed():
    """Main seeding function."""
    import django
    django.setup()

    from apps.core.models import Entity
    from apps.invoicing.models import Invoice, InvoiceLineItem
    from apps.payments.models import Payment, PaymentEvent
    from apps.core.choices import PaymentStatus, InvoiceStatus
    from apps.core.utils import generate_idempotency_key
    from apps.accounting.models import AccountMapping

    print("=" * 50)
    print("  Finsio — Seeding Development Data")
    print("=" * 50)
    print()

    # ── 1. Entity ──
    entity, created = Entity.objects.get_or_create(
        slug="acme",
        defaults={
            "name": "Acme Corporation",
            "base_currency": "USD",
            "beancount_entity_name": "Acme",
        },
    )
    print(f"  {'Created' if created else 'Found'} entity: {entity.name}")

    # ── 2. Account Mappings ──
    mappings = [
        ("1000", "Assets:Cash"),
        ("1100", "Assets:Bank:Operating"),
        ("1200", "Assets:AccountsReceivable"),
        ("1300", "Assets:PaymentProcessors:Stripe"),
        ("1310", "Assets:PaymentProcessors:Paypal"),
        ("2000", "Liabilities:AccountsPayable"),
        ("2100", "Liabilities:SalesTaxPayable"),
        ("3000", "Equity:RetainedEarnings"),
        ("4000", "Income:Revenue:General"),
        ("4100", "Income:Revenue:Subscription"),
        ("4200", "Income:Revenue:Services"),
        ("5000", "Expenses:Operating"),
        ("5100", "Expenses:PaymentProcessingFees"),
        ("5200", "Expenses:Software"),
        ("5300", "Expenses:Office"),
    ]

    mapping_count = 0
    for code, beancount_name in mappings:
        _, was_created = AccountMapping.objects.get_or_create(
            entity=entity,
            ledger_account_code=code,
            defaults={"finsio_concept": code, "ledger_account_name": beancount_name},
        )
        if was_created:
            mapping_count += 1
    print(f"  Created {mapping_count} account mappings ({len(mappings)} total)")

    # ── 3. Invoices ──
    invoices_data = [
        {
            "number": "INV-ACME-000001",
            "customer_name": "Bob's Burgers",
            "customer_email": "bob@burgers.example",
            "customer_id": "cust_001",
            "status": InvoiceStatus.PAID,
            "issue_date": date.today() - timedelta(days=45),
            "due_date": date.today() - timedelta(days=15),
            "paid_at": date.today() - timedelta(days=10),
            "items": [
                ("API Access — Professional Plan", 1, Decimal("299.00"), Decimal("0.08"), "Subscription"),
                ("Custom Integration Setup", 8, Decimal("150.00"), Decimal("0"), "Services"),
                ("Data Migration Service", 1, Decimal("500.00"), Decimal("0"), "Services"),
            ],
        },
        {
            "number": "INV-ACME-000002",
            "customer_name": "Wayne Enterprises",
            "customer_email": "bruce@wayne.example",
            "customer_id": "cust_002",
            "status": InvoiceStatus.PENDING,
            "issue_date": date.today() - timedelta(days=10),
            "due_date": date.today() + timedelta(days=20),
            "items": [
                ("Enterprise API License", 1, Decimal("999.00"), Decimal("0.10"), "Subscription"),
                ("Dedicated Support — 40 hours", 40, Decimal("125.00"), Decimal("0"), "Services"),
            ],
        },
        {
            "number": "INV-ACME-000003",
            "customer_name": "Stark Industries",
            "customer_email": "tony@stark.example",
            "customer_id": "cust_003",
            "status": InvoiceStatus.OVERDUE,
            "issue_date": date.today() - timedelta(days=60),
            "due_date": date.today() - timedelta(days=30),
            "items": [
                ("Annual API License", 1, Decimal("4999.00"), Decimal("0.08"), "Subscription"),
            ],
        },
        {
            "number": "INV-ACME-000004",
            "customer_name": "Smallville LLC",
            "customer_email": "clark@smallville.example",
            "customer_id": "cust_004",
            "status": InvoiceStatus.PARTIAL,
            "issue_date": date.today() - timedelta(days=20),
            "due_date": date.today() + timedelta(days=10),
            "items": [
                ("API Access — Growth Plan", 1, Decimal("149.00"), Decimal("0"), "Subscription"),
                ("Training Workshop", 2, Decimal("750.00"), Decimal("0.08"), "Services"),
            ],
        },
    ]

    invoice_objects = []
    for inv_data in invoices_data:
        invoice, was_created = Invoice.objects.get_or_create(
            number=inv_data["number"],
            defaults={
                "entity": entity,
                "customer_name": inv_data["customer_name"],
                "customer_email": inv_data["customer_email"],
                "customer_id": inv_data["customer_id"],
                "status": inv_data["status"],
                "issue_date": inv_data["issue_date"],
                "due_date": inv_data["due_date"],
                "paid_at": inv_data.get("paid_at"),
                "currency": "USD",
            },
        )

        if was_created:
            for desc, qty, price, tax, cat in inv_data["items"]:
                InvoiceLineItem.objects.create(
                    invoice=invoice,
                    description=desc,
                    quantity=qty,
                    unit_price=price,
                    tax_rate=tax,
                    category=cat,
                )
            invoice.recalculate()

            # If paid, set the paid amounts
            if inv_data["status"] == InvoiceStatus.PAID:
                invoice.amount_paid = invoice.total
                invoice.amount_due = Decimal("0")
                invoice.save(update_fields=["amount_paid", "amount_due"])

            # If partial, set partial payment
            if inv_data["status"] == InvoiceStatus.PARTIAL:
                partial_amount = invoice.total / 2
                invoice.amount_paid = partial_amount
                invoice.amount_due = invoice.total - partial_amount
                invoice.save(update_fields=["amount_paid", "amount_due"])

        invoice_objects.append(invoice)
        action = "Created" if was_created else "Found"
        print(f"  {action} invoice: {invoice.number} [{invoice.status}] {invoice.total} {invoice.currency}")

    # ── 4. Payments ──
    payments_data = [
        {
            "amount": Decimal("1649.92"),
            "currency": "USD",
            "processor": "stripe",
            "status": PaymentStatus.PAID,
            "external_id": "pi_acme_001",
            "customer_id": "cust_001",
            "customer_email": "bob@burgers.example",
            "description": "Payment for INV-ACME-000001",
            "reference": "INV-ACME-000001",
            "idempotency_suffix": "seed_001",
            "invoice_index": 0,
        },
        {
            "amount": Decimal("500.00"),
            "currency": "USD",
            "processor": "paypal",
            "status": PaymentStatus.PAID,
            "external_id": "PAY-acme-002",
            "customer_id": "cust_004",
            "customer_email": "clark@smallville.example",
            "description": "Partial payment for INV-ACME-000004",
            "reference": "INV-ACME-000004",
            "idempotency_suffix": "seed_002",
            "invoice_index": 3,
        },
        {
            "amount": Decimal("999.00"),
            "currency": "USD",
            "processor": "stripe",
            "status": PaymentStatus.PREPARED,
            "external_id": None,
            "customer_id": "cust_002",
            "customer_email": "bruce@wayne.example",
            "description": "Pending payment for INV-ACME-000002",
            "reference": "INV-ACME-000002",
            "idempotency_suffix": "seed_003",
            "invoice_index": 1,
        },
        {
            "amount": Decimal("250.00"),
            "currency": "USD",
            "processor": "stripe",
            "status": PaymentStatus.FAILED,
            "external_id": "pi_acme_004",
            "customer_id": "cust_003",
            "customer_email": "tony@stark.example",
            "description": "Failed payment attempt for INV-ACME-000003",
            "reference": "INV-ACME-000003",
            "idempotency_suffix": "seed_004",
            "invoice_index": 2,
        },
    ]

    today = date.today()
    for pdata in payments_data:
        idem_key = generate_idempotency_key("seed", pdata["idempotency_suffix"])

        payment, was_created = Payment.objects.get_or_create(
            idempotency_key=idem_key,
            defaults={
                "amount": pdata["amount"],
                "currency": pdata["currency"],
                "processor": pdata["processor"],
                "status": pdata["status"],
                "external_id": pdata["external_id"],
                "customer_id": pdata["customer_id"],
                "customer_email": pdata["customer_email"],
                "description": pdata["description"],
                "reference": pdata["reference"],
                "invoice": invoice_objects[pdata["invoice_index"]],
            },
        )

        if was_created:
            # Set timestamps based on status
            if payment.status == PaymentStatus.PAID:
                payment.paid_at = payment.created_at
                payment.save(update_fields=["paid_at"])
                PaymentEvent.objects.create(
                    payment=payment,
                    event_type=PaymentEvent.EventType.STATUS_CHANGED,
                    old_status=PaymentStatus.NEW,
                    new_status=PaymentStatus.PAID,
                    data={"source": "seed"},
                )
            elif payment.status == PaymentStatus.FAILED:
                payment.failed_at = payment.created_at
                payment.provider_metadata = {"failure_reason": "Card declined — insufficient funds"}
                payment.save(update_fields=["failed_at", "provider_metadata"])
                PaymentEvent.objects.create(
                    payment=payment,
                    event_type=PaymentEvent.EventType.STATUS_CHANGED,
                    old_status=PaymentStatus.NEW,
                    new_status=PaymentStatus.FAILED,
                    data={"failure_reason": "Card declined"},
                )

        action = "Created" if was_created else "Found"
        print(f"  {action} payment: {str(payment.id)[:8]}... [{payment.status}] {payment.amount} {payment.currency} via {payment.processor}")

    # ── Summary ──
    print()
    print("=" * 50)
    print(f"  Entity:      {Entity.objects.count()}")
    print(f"  Accounts:    {AccountMapping.objects.count()}")
    print(f"  Invoices:    {Invoice.objects.count()}")
    print(f"  Line Items:  {InvoiceLineItem.objects.count()}")
    print(f"  Payments:    {Payment.objects.count()}")
    print(f"  Events:      {PaymentEvent.objects.count()}")
    print("=" * 50)
    print("  Seed complete.")


if __name__ == "__main__":
    seed()
