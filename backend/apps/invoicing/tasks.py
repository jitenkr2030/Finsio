"""
Celery tasks for the Invoicing app.

Periodic tasks (run by Celery Beat):
  - check_overdue_invoices:  Daily, marks overdue invoices
  - sync_accounting:         Daily, syncs recent payments to beancount
  - send_payment_reminders:  Weekly, notifies customers of pending invoices
"""

from celery import shared_task
from datetime import date, timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task(name="apps.invoicing.check_overdue_invoices")
def check_overdue_invoices():
    """
    Daily task: mark invoices past their due date as overdue.

    Runs at 06:00 UTC via Celery Beat.
    """
    from .models import Invoice

    overdue_candidates = Invoice.objects.filter(
        status__in=["pending", "partial"],
        due_date__lt=date.today(),
    )

    count = 0
    for invoice in overdue_candidates:
        invoice.mark_overdue()
        count += 1

    logger.info("Marked %d invoices as overdue", count)
    return {"marked_overdue": count}


@shared_task(name="apps.invoicing.sync_accounting")
def sync_accounting():
    """
    Daily task: ensure beancount files are in sync.

    Runs reconciliation for the past 7 days to catch
    any payments that weren't synced in real-time.

    Runs at 07:00 UTC via Celery Beat.
    """
    from apps.accounting.services.reconciliation_service import ReconciliationService

    end = date.today()
    start = end - timedelta(days=7)

    result = ReconciliationService.reconcile_date_range(start, end)
    logger.info("Daily accounting sync: %s", result)
    return result


@shared_task(name="apps.invoicing.send_payment_reminders")
def send_payment_reminders():
    """
    Weekly task: send payment reminder emails for pending invoices.

    Sends reminders for invoices that are:
      - 7 days before due date
      - On the due date
      - 7 days overdue

    Runs every Monday at 09:00 UTC via Celery Beat.
    """
    from .models import Invoice

    today = date.today()
    reminder_dates = [
        today + timedelta(days=7),  # 7 days before due
        today,                       # Due today
        today - timedelta(days=7),  # 7 days overdue
    ]

    invoices = Invoice.objects.filter(
        status__in=["pending", "partial", "overdue"],
        due_date__in=reminder_dates,
    )

    sent = 0
    for invoice in invoices:
        _send_reminder_email(invoice)
        sent += 1

    logger.info("Sent %d payment reminders", sent)
    return {"reminders_sent": sent}


def _send_reminder_email(invoice):
    """Send a payment reminder email for an invoice."""
    from django.core.mail import send_mail

    days_until_due = (invoice.due_date - date.today()).days
    if days_until_due > 0:
        subject = f"Payment reminder: Invoice {invoice.number} due in {days_until_due} days"
    elif days_until_due == 0:
        subject = f"Payment due today: Invoice {invoice.number}"
    else:
        subject = f"Overdue: Invoice {invoice.number} is {abs(days_until_due)} days past due"

    message = (
        f"Dear {invoice.customer_name},\n\n"
        f"This is a reminder that invoice {invoice.number} for "
        f"{invoice.amount_due} {invoice.currency} is "
        f"{'due today' if days_until_due == 0 else f'due on {invoice.due_date}'}."
        f"\n\n"
    )

    if invoice.payment_url:
        message += f"Pay online: {invoice.payment_url}\n\n"

    message += "Thank you for your business.\n"

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email="billing@finsio.local",
            recipient_list=[invoice.customer_email],
            fail_silently=False,
        )
        logger.info("Reminder sent for invoice %s to %s", invoice.number, invoice.customer_email)
    except Exception as e:
        logger.error("Failed to send reminder for invoice %s: %s", invoice.number, e)


@shared_task(name="apps.invoicing.generate_monthly_report")
def generate_monthly_report(entity_slug: str = "default"):
    """
    Monthly task: generate a revenue report for the previous month.

    Runs on the 1st of each month at 08:00 UTC via Celery Beat.
    """
    from apps.accounting.services.reporting_service import ReportingService

    today = date.today()
    first_of_this_month = today.replace(day=1)
    last_of_prev_month = first_of_this_month - timedelta(days=1)
    first_of_prev_month = last_of_prev_month.replace(day=1)

    report = ReportingService.get_revenue_summary(
        entity_slug=entity_slug,
        date_from=first_of_prev_month,
        date_to=last_of_prev_month,
    )

    logger.info("Monthly report for %s: %s", entity_slug, report)
    return report
