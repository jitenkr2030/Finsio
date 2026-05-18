"""
Finsio — Financial Operations Platform

Django project package. Imports the Celery application
so that autodiscover_tasks() runs when Django starts.
"""

from .celery import app as celery_app

__all__ = ["celery_app"]
__version__ = "1.0.0"
