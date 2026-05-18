"""
Reporting service.

Generates financial reports by querying django-ledger's
AccountModel and TransactionModel, then formatting for
the Finsio API.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any
from uuid import UUID

from apps.core.models import Entity

logger = logging.getLogger(__name__)


class ReportingService:
    """
    Generates financial reports for an entity.

    Uses django-ledger's double-entry data to produce:
    - Balance sheet
    - Profit & Loss statement
    - Trial balance
    - Account ledger details
    """

    def __init__(self, entity_id: UUID):
        self.entity = Entity.objects.get(id=entity_id)
        self._entity_model = None

    def _get_ledger_entity(self):
        """Get the django-ledger EntityModel instance."""
        if self._entity_model is None:
            try:
                from django_ledger.models.entity import EntityModel
                self._entity_model = EntityModel.objects.get(
                    uuid=self.entity.ledger_entity_id,
                )
            except Exception as e:
                logger.warning("Could not load django-ledger entity: %s", e)
                return None
        return self._entity_model

    def balance_sheet(self) -> dict[str, Any]:
        """
        Generate a balance sheet.

        Assets = Liabilities + Equity
        """
        entity = self._get_ledger_entity()
        if entity is None:
            return {"error": "django-ledger entity not found"}

        try:
            from django_ledger.models import AccountModel

            accounts = AccountModel.objects.filter(
                coa_model__entity__uuid=self.entity.ledger_entity_id,
            )

            assets = []
            liabilities = []
            equity = []

            for acct in accounts:
                balance = float(getattr(acct, "balance", 0) or 0)
                entry = {
                    "code": acct.code,
                    "name": acct.name,
                    "balance": balance,
                }
                role = getattr(acct, "role", "")

                if role and role.startswith("asset"):
                    assets.append(entry)
                elif role and role.startswith("liability"):
                    liabilities.append(entry)
                elif role and role.startswith("equity"):
                    equity.append(entry)

            total_assets = sum(a["balance"] for a in assets)
            total_liabilities = sum(l["balance"] for l in liabilities)
            total_equity = sum(e["balance"] for e in equity)

            return {
                "entity": self.entity.name,
                "date": str(self.entity.updated_at.date()),
                "assets": {
                    "accounts": assets,
                    "total": total_assets,
                },
                "liabilities": {
                    "accounts": liabilities,
                    "total": total_liabilities,
                },
                "equity": {
                    "accounts": equity,
                    "total": total_equity,
                },
                "balanced": abs(total_assets - (total_liabilities + total_equity)) < 0.01,
            }

        except Exception as e:
            logger.error("Balance sheet generation failed: %s", e)
            return {"error": str(e)}

    def profit_and_loss(self) -> dict[str, Any]:
        """
        Generate a P&L statement.

        Revenue - Expenses = Net Income
        """
        try:
            from django_ledger.models import AccountModel

            accounts = AccountModel.objects.filter(
                coa_model__entity__uuid=self.entity.ledger_entity_id,
            )

            revenue = []
            expenses = []

            for acct in accounts:
                balance = float(getattr(acct, "balance", 0) or 0)
                entry = {
                    "code": acct.code,
                    "name": acct.name,
                    "balance": balance,
                }
                role = getattr(acct, "role", "")

                if role and role.startswith("in"):
                    revenue.append(entry)
                elif role and role.startswith("ex"):
                    expenses.append(entry)

            total_revenue = sum(r["balance"] for r in revenue)
            total_expenses = sum(e["balance"] for e in expenses)

            return {
                "entity": self.entity.name,
                "period": str(self.entity.updated_at.date()),
                "revenue": {
                    "accounts": revenue,
                    "total": total_revenue,
                },
                "expenses": {
                    "accounts": expenses,
                    "total": total_expenses,
                },
                "net_income": total_revenue - total_expenses,
            }

        except Exception as e:
            logger.error("P&L generation failed: %s", e)
            return {"error": str(e)}

    def trial_balance(self) -> dict[str, Any]:
        """Generate a trial balance (all debits should equal all credits)."""
        try:
            from django_ledger.models import AccountModel

            accounts = AccountModel.objects.filter(
                coa_model__entity__uuid=self.entity.ledger_entity_id,
            )

            entries = []
            total_debit = 0
            total_credit = 0

            for acct in accounts:
                balance = float(getattr(acct, "balance", 0) or 0)
                is_debit = getattr(acct, "is_debit", balance > 0)

                debit = balance if (balance > 0) else 0
                credit = abs(balance) if (balance < 0) else 0

                entries.append({
                    "code": acct.code,
                    "name": acct.name,
                    "debit": debit,
                    "credit": credit,
                })

                total_debit += debit
                total_credit += credit

            return {
                "entity": self.entity.name,
                "entries": entries,
                "total_debit": total_debit,
                "total_credit": total_credit,
                "balanced": abs(total_debit - total_credit) < 0.01,
            }

        except Exception as e:
            logger.error("Trial balance generation failed: %s", e)
            return {"error": str(e)}

    def generate_all(self) -> dict[str, Any]:
        """Generate all reports at once."""
        return {
            "balance_sheet": self.balance_sheet(),
            "profit_and_loss": self.profit_and_loss(),
            "trial_balance": self.trial_balance(),
        }
