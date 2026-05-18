"""
Beancount file parser for Finsio.

Reads .beancount files using the beancount library's parser
and provides structured access to accounts, transactions,
and balances for cross-referencing with django-ledger data.
"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)


class BeancountParser:
    """
    Reads .beancount files and extracts structured data.

    Usage:
        parser = BeancountParser()
        entries, errors, options = parser.load_main()
        transactions = parser.get_transactions_for_date_range("2025-01-01", "2025-12-31")
    """

    def __init__(self, base_path: Path | None = None):
        self.base_path = base_path or settings.BEANCOUNT_PATH

    def load_main(self) -> tuple | None:
        """
        Load and parse the main.beancount file.

        Returns:
            (entries, errors, options) tuple from beancount.loader,
            or None if main.beancount doesn't exist.
        """
        from beancount import loader

        main_file = self.base_path / "main.beancount"
        if not main_file.exists():
            logger.warning("main.beancount not found at %s", main_file)
            return None

        entries, errors, options = loader.load_file(str(main_file))

        if errors:
            for error in errors:
                logger.warning("Beancount parse error: %s", error)

        return entries, errors, options

    def get_accounts(self) -> list[str]:
        """Get all defined account names."""
        from beancount.core import getters

        result = self.load_main()
        if result is None:
            return []

        entries, _, _ = result
        return [str(acc) for acc in getters.get_accounts(entries)]

    def get_transactions_for_date_range(
        self,
        start: str,
        end: str,
    ) -> list[dict[str, Any]]:
        """
        Retrieve all transactions within a date range.

        Returns a list of dicts with:
            date, narration, payee, postings, tags, links
        """
        from beancount.core.data import Transaction

        result = self.load_main()
        if result is None:
            return []

        entries, _, _ = result
        start_date = date.fromisoformat(start)
        end_date = date.fromisoformat(end)

        transactions = []
        for entry in entries:
            if isinstance(entry, Transaction) and start_date <= entry.date <= end_date:
                transactions.append({
                    "date": entry.date.isoformat(),
                    "narration": entry.narration,
                    "payee": entry.payee or "",
                    "flag": entry.flag,
                    "postings": [
                        {
                            "account": str(p.account),
                            "amount": str(p.units.number),
                            "currency": str(p.units.currency),
                        }
                        for p in entry.postings
                    ],
                    "tags": list(entry.tags) if entry.tags else [],
                    "links": list(entry.links) if entry.links else [],
                })

        return transactions

    def get_account_balance(self, account: str, as_of: str | None = None) -> dict[str, str]:
        """
        Get the balance of a specific account.

        Returns:
            {"amount": "1234.56", "currency": "USD"}
        """
        from beancount.core import realization
        from beancount.core.data import Transaction

        result = self.load_main()
        if result is None:
            return {"amount": "0.00", "currency": "USD"}

        entries, _, _ = result

        if as_of:
            cutoff = date.fromisoformat(as_of)
            entries = [e for e in entries if not isinstance(e, Transaction) or e.date <= cutoff]

        real_account = realization.realize(entries)

        # Find the account in the tree
        node = realization.get(real_account, account)
        if node is None or node.balance.is_empty():
            return {"amount": "0.00", "currency": "USD"}

        # Return the first position
        for currency, position in node.balance.items():
            return {
                "amount": str(position.number),
                "currency": str(currency),
            }

        return {"amount": "0.00", "currency": "USD"}

    def get_errors(self) -> list[dict[str, str]]:
        """Get all parse errors from the beancount files."""
        result = self.load_main()
        if result is None:
            return []

        _, errors, _ = result
        return [
            {
                "source": str(e.source) if e.source else "",
                "message": e.message,
                "entry": str(e.entry) if e.entry else "",
            }
            for e in errors
        ]

    def validate(self) -> dict[str, Any]:
        """
        Validate all beancount files and return a summary.

        Returns:
            {
                "valid": bool,
                "entries_count": int,
                "errors_count": int,
                "errors": [...],
                "accounts_count": int,
            }
        """
        result = self.load_main()
        if result is None:
            return {
                "valid": False,
                "entries_count": 0,
                "errors_count": 0,
                "errors": [{"message": "main.beancount not found"}],
                "accounts_count": 0,
            }

        entries, errors, options = result
        return {
            "valid": len(errors) == 0,
            "entries_count": len(entries),
            "errors_count": len(errors),
            "errors": self.get_errors()[:20],
            "accounts_count": len(self.get_accounts()),
        }
