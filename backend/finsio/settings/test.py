"""
Test settings for Finsio.

Inherits from base.py with in-memory SQLite,
synchronous Celery execution, and fake API keys.
"""

from .base import *  # noqa: F401,F403

# ──────────────────────────────────────────────
# Database — fast in-memory SQLite
# ──────────────────────────────────────────────
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
}

# ──────────────────────────────────────────────
# Celery — run tasks synchronously in tests
# ──────────────────────────────────────────────
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# ──────────────────────────────────────────────
# Password hashing — fast for tests
# ──────────────────────────────────────────────
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# ──────────────────────────────────────────────
# Payment keys — fake values
# ──────────────────────────────────────────────
STRIPE_SECRET_KEY = "sk_test_fake_key_for_testing"
STRIPE_WEBHOOK_SECRET = "whsec_fake_secret_for_testing"
PAYPAL_CLIENT_ID = "fake_paypal_client_id"
PAYPAL_CLIENT_SECRET = "fake_paypal_client_secret"
BRAINTREE_MERCHANT_ID = "fake_merchant"
BRAINTREE_PUBLIC_KEY = "fake_public"
BRAINTREE_PRIVATE_KEY = "fake_private"

# ──────────────────────────────────────────────
# Internal auth
# ──────────────────────────────────────────────
BACKEND_INTERNAL_TOKEN = "test-internal-token"

# ──────────────────────────────────────────────
# Disable migrations for speed (optional)
# ──────────────────────────────────────────────
# class DisableMigrations:
#     def __contains__(self, item):
#         return True
#     def __getitem__(self, item):
#         return None
#
# MIGRATION_MODULES = DisableMigrations()

# ──────────────────────────────────────────────
# Logging — quiet during tests
# ──────────────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {
        "null": {
            "class": "logging.NullHandler",
        },
    },
    "root": {
        "handlers": ["null"],
        "level": "CRITICAL",
    },
}

# ──────────────────────────────────────────────
# Templates — fast backend
# ──────────────────────────────────────────────
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": False,
        "OPTIONS": {
            "context_processors": [],
        },
    },
]
