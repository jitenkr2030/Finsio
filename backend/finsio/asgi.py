"""
ASGI config for Finsio.

Used for async capabilities and WebSocket support (future).
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "finsio.settings.development")

application = get_asgi_application()
