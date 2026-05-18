"""
Celery application for Finsio.

Configures the task broker, autodiscovers tasks from all
installed apps, and defines periodic beat schedules.
"""

import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "finsio.settings.development")

app = Celery("finsio")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# ──────────────────────────────────────────────
# Periodic task schedule (Celery Beat)
# ──────────────────────────────────────────────
app.conf.beat_schedule = {
    # Check for overdue invoices every day at 06:00 UTC
    "check-overdue-invoices": {
        "task": "apps.invoicing.tasks.check_overdue_invoices",
        "schedule": crontab(hour=6, minute=0),
        "options": {"queue": "invoicing"},
    },
    # Sync accounting records to beancount every day at 07:00 UTC
    "sync-accounting-to-beancount": {
        "task": "apps.invoicing.tasks.sync_accounting",
        "schedule": crontab(hour=7, minute=0),
        "options": {"queue": "accounting"},
    },
    # Run reconciliation check weekly on Monday at 08:00 UTC
    "weekly-reconciliation": {
        "task": "apps.accounting.tasks.weekly_reconciliation",
        "schedule": crontab(hour=8, minute=0, day_of_week=1),
        "options": {"queue": "accounting"},
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Print request info — useful for debugging Celery connectivity."""
    print(f"Request: {self.request!r}")
