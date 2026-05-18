"""
URL routes for accounting API endpoints (under /internal/accounting/).
"""

from django.urls import path

from . import views

urlpatterns = [
    path("journal-entries", views.journal_entry_list, name="journal-entry-list"),
    path("journal-entries/create", views.journal_entry_create, name="journal-entry-create"),
    path("balance-sheet", views.balance_sheet, name="balance-sheet"),
    path("profit-loss", views.profit_loss, name="profit-loss"),
    path("ledger-accounts", views.ledger_accounts, name="ledger-accounts"),
    path("reconciliation", views.reconciliation_run, name="reconciliation-run"),
]
