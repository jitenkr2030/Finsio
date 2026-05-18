"""
Development settings for Finsio.

Inherits from base.py with debug mode enabled,
permissive CORS, SQL query logging, and email
output to the console.
"""

from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

# ──────────────────────────────────────────────
# CORS — wide open in development
# ──────────────────────────────────────────────
CORS_ALLOW_ALL_ORIGINS = True

# ──────────────────────────────────────────────
# Email — print to console
# ──────────────────────────────────────────────
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# ──────────────────────────────────────────────
# Debug toolbar (optional)
# ──────────────────────────────────────────────
try:
    import debug_toolbar  # noqa: F401
    INSTALLED_APPS += ["debug_toolbar"]  # noqa: F405
    MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]  # noqa: F405
    INTERNAL_IPS = ["127.0.0.1", "10.0.2.2"]
except ImportError:
    pass

# ──────────────────────────────────────────────
# Logging — verbose in development
# ──────────────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "DEBUG",
    },
    "loggers": {
        "django.db.backends": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "apps.payments": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "apps.accounting": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "apps.invoicing": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}

# Use Replit PostgreSQL (DATABASE_URL is set by the platform)
import dj_database_url, os
_db_url = os.environ.get("DATABASE_URL")
if _db_url:
    DATABASES = {
        "default": dj_database_url.config(
            default=_db_url,
            conn_max_age=600,
            conn_health_checks=False,
        )
    }
