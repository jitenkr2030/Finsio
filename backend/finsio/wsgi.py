"""
WSGI config for Finsio.

Used by Gunicorn in production and Django's `runserver` in development.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "finsio.settings.development")

application = get_wsgi_application()
