"""
Beancount transaction generator for Finsio.

Generates .beancount text entries from financial transactions.
Uses Jinja2 templates for clean, human-readable output.
Each entity has its own namespace in the beancount hierarchy
(e.g. "Acme:Assets:Bank:Operating").

Output files are date-partitioned under BEANCOUNT_PATH/transactions/
and included by main.beancount via glob.
"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from django.conf import settings
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

# Template environment
_TEMPLATE_DIR = Path(__file__).parent / "templates"
_jinja_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=True,
)


class BeancountGenerator:
    """
    Generates .beancount text for financial transactions.

    Usage:
        gen = BeancountGenerator("Acme")
        gen.generate_journal_entry(
            entry_date=date.today(),
            description="Office supplies",
            postings=[
                {"account": "Expenses:Office", "amount": Decimal("150.00"), "currency": "USD"},
                {"account": "Assets:Bank:Operating", "amount": Decimal("-150.00"), "currency": "USD"},
            ],
        )
    """

    def __init__(self, entity_name: str):
        self.entity_name = entity_name
        self.base_path = settings.BEANCOUNT_PATH / "transactions"
        self.base_path.mkdir(parents=True, exist_ok=True)

    def generate_journal_entry(
        self,
        entry_date: date,
        description: str,
        postings: list[dict[str, Any]],
        tags: list[str] | None = None,
        metadata: dict[str, str] | None = None,
        links: list[str] | None = None,
    ) -> str:
        """
        Generate a beancount transaction for a generic journal entry.

        Args:
            entry_date:  Transaction date
            description: Human-readable narration
            postings:    List of {"account": str, "amount": Decimal, "currency": str}
            tags:        Optional beancount tags (without # prefix)
            metadata:    Optional key-value metadata
            links:       Optional beancount links (without ^ prefix)

        Returns:
            The rendered beancount text
        """
        template = _jinja_env.get_template("transaction.tpl")

        rendered = template.render(
            date=entry_date.isoformat(),
            flag="*",
            payee="",
            narration=description,
            tags=[f"#{t}" for t in (tags or [])],
            links=[f"^{l}" for l in (links or [])],
            postings=[
                {
                    "account": self._qualify_account(p["account"]),
                    "amount": self._format_amount(p["amount"]),
                    "currency": p.get("currency", "USD"),
                }
                for p in postings
            ],
            metadata=metadata or {},
        )

        self._append_to_file(entry_date, rendered)
        return rendered

    def generate_invoice_entry(
        self,
        entry_date: date,
        invoice_number: str,
        customer_name: str,
        line_items: list[dict[str, Any]],
        currency: str = "USD",
    ) -> str:
        """
        Generate a beancount entry for an invoice (accrual basis).

        Debits Accounts Receivable, credits Revenue for each line item.
        """
        total = Decimal("0")
        postings = []

        for item in line_items:
            qty = Decimal(str(item.get("quantity", 1)))
            price = Decimal(str(item.get("unit_price", 0)))
            line_total = qty * price
            total += line_total

            category = item.get("category", "General")
            postings.append({
                "account": f"Income:Revenue:{category}",
                "amount": -line_total,
                "currency": currency,
            })

        postings.append({
            "account": "Assets:AccountsReceivable",
            "amount": total,
            "currency": currency,
        })

        return self.generate_journal_entry(
            entry_date=entry_date,
            description=f"Invoice {invoice_number} — {customer_name}",
            postings=postings,
            tags=["invoice"],
            metadata={
                "invoice": invoice_number,
                "customer": customer_name,
                "total": str(total),
            },
        )

    def generate_payment_entry(
        self,
        payment_date: date,
        payment_id: str,
        amount: Decimal,
        currency: str = "USD",
        processor: str = "stripe",
    ) -> str:
        """
        Generate a beancount entry for a received payment.

        Debits the processor account, credits Accounts Receivable.
        """
        return self.generate_journal_entry(
            entry_date=payment_date,
            description=f"Payment received {payment_id} via {processor}",
            postings=[
                {
                    "account": f"Assets:PaymentProcessors:{processor.title()}",
                    "amount": amount,
                    "currency": currency,
                },
                {
                    "account": "Assets:AccountsReceivable",
                    "amount": -amount,
                    "currency": currency,
                },
            ],
            tags=["payment"],
            metadata={
                "payment_id": payment_id,
                "processor": processor,
            },
        )

    def generate_refund_entry(
        self,
        refund_date: date,
        payment_id: str,
        amount: Decimal,
        currency: str = "USD",
        processor: str = "stripe",
    ) -> str:
        """
        Generate a beancount entry for a payment refund.

        Debits Refunds (contra-revenue), credits the processor account.
        """
        return self.generate_journal_entry(
            entry_date=refund_date,
            description=f"Refund for payment {payment_id} via {processor}",
            postings=[
                {
                    "account": "Income:Refunds",
                    "amount": amount,
                    "currency": currency,
                },
                {
                    "account": f"Assets:PaymentProcessors:{processor.title()}",
                    "amount": -amount,
                    "currency": currency,
                },
            ],
            tags=["refund"],
            metadata={
                "payment_id": payment_id,
                "processor": processor,
            },
        )

    def generate_fee_entry(
        self,
        fee_date: date,
        payment_id: str,
        fee_amount: Decimal,
        currency: str = "USD",
        processor: str = "stripe",
    ) -> str:
        """
        Generate a beancount entry for a payment processing fee.
        """
        return self.generate_journal_entry(
            entry_date=fee_date,
            description=f"Processing fee for {payment_id} via {processor}",
            postings=[
                {
                    "account": "Expenses:PaymentProcessingFees",
                    "amount": fee_amount,
                    "currency": currency,
                },
                {
                    "account": f"Assets:PaymentProcessors:{processor.title()}",
                    "amount": -fee_amount,
                    "currency": currency,
                },
            ],
            tags=["fee"],
            metadata={
                "payment_id": payment_id,
                "processor": processor,
            },
        )

    def _qualify_account(self, account: str) -> str:
        """Prefix account with entity name if not already qualified."""
        if account.startswith(f"{self.entity_name}:"):
            return account
        if account.startswith(("Assets:", "Liabilities:", "Equity:",
                               "Income:", "Expenses:")):
            return f"{self.entity_name}:{account}"
        return account

    @staticmethod
    def _format_amount(amount: Decimal | float | int) -> str:
        """Format amount with exactly 2 decimal places."""
        d = Decimal(str(amount))
        return f"{d:.2f}"

    def _append_to_file(self, entry_date: date, text: str):
        """Append rendered beancount text to the date-partitioned file."""
        file_path = self.base_path / f"{entry_date.isoformat()}.beancount"
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(text)
            f.write("\n")
        logger.debug("Appended beancount entry to %s", file_path)
