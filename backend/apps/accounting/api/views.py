"""
Accounting API views for Finsio.

Provides journal entry CRUD, financial reports (balance sheet,
P&L), and ledger account listing. Every journal entry is
written to both django-ledger and a .beancount audit file.
"""

import logging
from datetime import date

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from ..beancount.sync import BeancountSync
from ..services.reporting_service import ReportingService
from ..services.reconciliation_service import ReconciliationService

logger = logging.getLogger(__name__)


@api_view(["POST"])
def journal_entry_create(request: Request) -> Response:
    """
    POST /internal/accounting/journal-entries/create

    Creates a double-entry journal entry in django-ledger
    and syncs it to the beancount audit trail.

    Body:
        entity      (required) Entity slug
        date        (required) YYYY-MM-DD
        description (required) Narration
        entries     (required) [{account, debit, credit}, ...]
        tags        (optional) ["tag1", "tag2"]
    """
    data = request.data
    entity_slug = data.get("entity")
    entry_date = data.get("date", date.today().isoformat())
    description = data.get("description", "")
    entries = data.get("entries", [])

    if not entity_slug:
        return Response(
            {"error": "entity is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not entries:
        return Response(
            {"error": "entries array is required with at least one posting"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Verify debits == credits
    total_debits = sum(float(e.get("debit", 0)) for e in entries)
    total_credits = sum(float(e.get("credit", 0)) for e in entries)
    if abs(total_debits - total_credits) > 0.01:
        return Response(
            {
                "error": "unbalanced_entry",
                "message": f"Debits ({total_debits}) must equal credits ({total_credits})",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Get the entity
    from apps.core.models import Entity
    try:
        entity = Entity.objects.get(slug=entity_slug)
    except Entity.DoesNotExist:
        return Response(
            {"error": f"Entity '{entity_slug}' not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Create in django-ledger
    from django_ledger.models.entity import EntityModel
    try:
        ledger_entity = EntityModel.objects.get(pk=entity.ledger_entity_id)
    except EntityModel.DoesNotExist:
        return Response(
            {"error": f"Ledger entity not found for '{entity_slug}'"},
            status=status.HTTP_404_NOT_FOUND,
        )

    je = ledger_entity.create_journal_entry(
        je_date=date.fromisoformat(entry_date),
        description=description,
    )

    for entry in entries:
        account_code = entry.get("account")
        debit = float(entry.get("debit", 0))
        credit = float(entry.get("credit", 0))

        if debit > 0:
            je.add_activity(account=account_code, amount=debit, tx_type="D")
        if credit > 0:
            je.add_activity(account=account_code, amount=credit, tx_type="C")

    je.lock()
    je.post()

    # Sync to beancount
    beancount_text = BeancountSync.sync_journal_entry(je, entity.beancount_entity_name)

    return Response({
        "journal_entry_id": str(je.pk),
        "entity": entity_slug,
        "date": entry_date,
        "description": description,
        "status": "posted",
        "total_debits": total_debits,
        "total_credits": total_credits,
        "beancount_synced": beancount_text is not None,
    }, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def journal_entry_list(request: Request) -> Response:
    """
    GET /internal/accounting/journal-entries

    List journal entries with optional filters.
    """
    from django_ledger.models.journal_entry import JournalEntryModel

    queryset = JournalEntryModel.objects.all()

    entity_slug = request.query_params.get("entity")
    if entity_slug:
        from apps.core.models import Entity
        try:
            entity = Entity.objects.get(slug=entity_slug)
            if entity.ledger_entity_id:
                queryset = queryset.filter(entity_id=entity.ledger_entity_id)
        except Entity.DoesNotExist:
            return Response({"error": "Entity not found"}, status=404)

    date_from = request.query_params.get("date_from")
    date_to = request.query_params.get("date_to")
    if date_from:
        queryset = queryset.filter(je_date__gte=date_from)
    if date_to:
        queryset = queryset.filter(je_date__lte=date_to)

    page = max(int(request.query_params.get("page", 1)), 1)
    page_size = min(int(request.query_params.get("page_size", 50)), 200)
    offset = (page - 1) * page_size

    total = queryset.count()
    entries = queryset.order_by("-je_date")[offset:offset + page_size]

    return Response({
        "total": total,
        "page": page,
        "page_size": page_size,
        "results": [
            {
                "id": str(je.pk),
                "date": je.je_date.isoformat(),
                "description": je.description,
                "posted": je.posted,
                "locked": je.locked,
            }
            for je in entries
        ],
    })


@api_view(["GET"])
def balance_sheet(request: Request) -> Response:
    """
    GET /internal/accounting/balance-sheet

    Generate a balance sheet for an entity.
    """
    entity_slug = request.query_params.get("entity")
    as_of = request.query_params.get("as_of")

    if not entity_slug:
        return Response(
            {"error": "entity parameter is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    as_of_date = date.fromisoformat(as_of) if as_of else date.today()
    report = ReportingService.get_balance_sheet(entity_slug, as_of_date)
    return Response(report)


@api_view(["GET"])
def profit_loss(request: Request) -> Response:
    """
    GET /internal/accounting/profit-loss

    Generate a Profit & Loss statement for a date range.
    """
    entity_slug = request.query_params.get("entity")
    date_from = request.query_params.get("date_from")
    date_to = request.query_params.get("date_to")

    if not entity_slug or not date_from or not date_to:
        return Response(
            {"error": "entity, date_from, and date_to are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    report = ReportingService.get_profit_loss(
        entity_slug,
        date.fromisoformat(date_from),
        date.fromisoformat(date_to),
    )
    return Response(report)


@api_view(["GET"])
def ledger_accounts(request: Request) -> Response:
    """
    GET /internal/accounting/ledger-accounts

    List all active accounts in the Chart of Accounts.
    """
    entity_slug = request.query_params.get("entity")

    if not entity_slug:
        return Response(
            {"error": "entity parameter is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    from apps.core.models import Entity

    try:
        entity = Entity.objects.get(slug=entity_slug)
    except Entity.DoesNotExist:
        return Response(
            {"error": f"Entity '{entity_slug}' not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    if not entity.ledger_entity_id:
        return Response({
            "entity": entity_slug,
            "accounts": [],
            "message": "Entity not yet linked to a ledger",
        })

    from django_ledger.models.entity import EntityModel

    try:
        ledger_entity = EntityModel.objects.get(pk=entity.ledger_entity_id)
    except EntityModel.DoesNotExist:
        return Response({
            "entity": entity_slug,
            "accounts": [],
            "message": "Ledger entity not found",
        })

    accounts = ledger_entity.chartofaccounts_model.coaaccountmodel_set.filter(
        active=True,
    ).order_by("code")

    return Response({
        "entity": entity_slug,
        "accounts": [
            {
                "code": acc.code,
                "name": acc.name,
                "role": acc.role,
                "active": acc.active,
            }
            for acc in accounts
        ],
    })


@api_view(["POST"])
def reconciliation_run(request: Request) -> Response:
    """
    POST /internal/accounting/reconciliation

    Run reconciliation for a date range.
    Detects unsynced payments and auto-fixes them.
    """
    date_from = request.data.get("date_from")
    date_to = request.data.get("date_to")

    if not date_from or not date_to:
        return Response(
            {"error": "date_from and date_to are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    from datetime import date as date_cls
    result = ReconciliationService.reconcile_date_range(
        date_cls.fromisoformat(date_from),
        date_cls.fromisoformat(date_to),
    )
    return Response(result)
