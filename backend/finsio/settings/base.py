"""
Base Django settings for Finsio.

All environment-specific settings inherit from here.
Sensible defaults for local development; override in
production.py, development.py, or test.py.
"""

from pathlib import Path

import dj_database_url
import environ

env = environ.Env()

# ──────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent
APPS_DIR = BASE_DIR / "apps"
BEANCOUNT_PATH = Path(env("BEANCOUNT_PATH", default=str(BASE_DIR.parent / "beancount")))

# ──────────────────────────────────────────────
# Core
# ──────────────────────────────────────────────
SECRET_KEY = env("DJANGO_SECRET_KEY", default="insecure-dev-key-change-in-production")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["*"])
ROOT_URLCONF = "finsio.urls"
WSGI_APPLICATION = "finsio.wsgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ──────────────────────────────────────────────
# Applications
# ──────────────────────────────────────────────
INSTALLED_APPS = [
    # Django built-in
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "django_filters",
    "corsheaders",
    "django_celery_beat",
    "django_celery_results",
    "django_extensions",
    # django-ledger (double-entry accounting)
    "django_ledger",
    # django-payments (jazzband universal payments)
    "payments",
    # Finsio apps
    "apps.core",
    "apps.payments",
    "apps.accounting",
    "apps.invoicing",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.middleware.InternalAuthMiddleware",
]

# ──────────────────────────────────────────────
# Templates
# ──────────────────────────────────────────────
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ──────────────────────────────────────────────
# Database
# ──────────────────────────────────────────────
DATABASES = {
    "default": dj_database_url.config(
        default=env("DATABASE_URL", default="postgres://finsio:finsio@localhost:5432/finsio"),
        conn_max_age=600,
        conn_health_checks=True,
    ),
}

# ──────────────────────────────────────────────
# Auth
# ──────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ──────────────────────────────────────────────
# REST Framework
# ──────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.core.authentication.InternalTokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
    ],
    "EXCEPTION_HANDLER": "apps.core.exceptions.custom_exception_handler",
}

# ──────────────────────────────────────────────
# Celery
# ──────────────────────────────────────────────
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/1")
CELERY_RESULT_BACKEND = "django-db"
CELERY_CACHE_BACKEND = "django-cache"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 300
CELERY_TASK_SOFT_TIME_LIMIT = 240
CELERY_TASK_ROUTES = {
    "apps.payments.tasks.*": {"queue": "payments"},
    "apps.accounting.tasks.*": {"queue": "accounting"},
    "apps.invoicing.tasks.*": {"queue": "invoicing"},
}

# ──────────────────────────────────────────────
# Payment providers
# ──────────────────────────────────────────────
STRIPE_SECRET_KEY = env("STRIPE_SECRET_KEY", default="")
STRIPE_WEBHOOK_SECRET = env("STRIPE_WEBHOOK_SECRET", default="")
PAYPAL_CLIENT_ID = env("PAYPAL_CLIENT_ID", default="")
PAYPAL_CLIENT_SECRET = env("PAYPAL_CLIENT_SECRET", default="")
PAYPAL_MODE = env("PAYPAL_MODE", default="sandbox")
BRAINTREE_MERCHANT_ID = env("BRAINTREE_MERCHANT_ID", default="")
BRAINTREE_PUBLIC_KEY = env("BRAINTREE_PUBLIC_KEY", default="")
BRAINTREE_PRIVATE_KEY = env("BRAINTREE_PRIVATE_KEY", default="")

# django-payments provider mapping
PAYMENT_VARIANTS = {
    "default": ("payments.stripe.StripeProvider", {
        "secret_key": STRIPE_SECRET_KEY,
    }),
    "paypal": ("payments.paypal.PaypalProvider", {
        "client_id": PAYPAL_CLIENT_ID,
        "secret": PAYPAL_CLIENT_SECRET,
        "sandbox": True,
    }),
}

# ──────────────────────────────────────────────
# Internal auth (Fusio gateway ↔ Django)
# ──────────────────────────────────────────────
BACKEND_INTERNAL_TOKEN = env("BACKEND_INTERNAL_TOKEN", default="change-me-in-production")

# ──────────────────────────────────────────────
# Static files
# ──────────────────────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

# ──────────────────────────────────────────────
# Internationalization
# ──────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ──────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "apps.payments": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "apps.accounting": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "apps.invoicing": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}


# ──────────────────────────────────────────────
# django-payments required settings
# ──────────────────────────────────────────────
PAYMENT_HOST = env("PAYMENT_HOST", default="localhost:8000")
PAYMENT_USES_SSL = False
PAYMENT_MODEL = "finsio_payments.Payment"

# ──────────────────────────────────────────────
# django-ledger
# ──────────────────────────────────────────────
DJANGO_LEDGER_USE_DEPRECATED_BEHAVIOR = False
