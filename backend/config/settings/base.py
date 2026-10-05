"""Réglages KEMTA communs à tous les environnements.

Principes :
- tout secret vient de l'environnement (.env), jamais du dépôt ;
- PostgreSQL + Redis en production, repli SQLite/locmem pour le développement
  local sur une machine sans Docker ;
- sécurité activée par défaut (durcissement affiné en production).
"""
from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path
from urllib.parse import unquote, urlparse

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT = BASE_DIR.parent


def env(key: str, default: str | None = None) -> str | None:
    value = os.environ.get(key)
    return default if value is None or value == "" else value


def env_bool(key: str, default: bool = False) -> bool:
    raw = os.environ.get(key)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def env_int(key: str, default: int) -> int:
    try:
        return int(os.environ[key])
    except (KeyError, TypeError, ValueError):
        return default


def env_list(key: str, default: str = "") -> list[str]:
    raw = env(key, default) or ""
    return [item.strip() for item in raw.split(",") if item.strip()]


# --- Sécurité ---------------------------------------------------------------
SECRET_KEY = env("SECRET_KEY", "dev-only-secret-change-me")
JWT_SECRET = env("JWT_SECRET", SECRET_KEY) or SECRET_KEY
DEBUG = env_bool("DEBUG", False)
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0,[::1]")

# Hôtes de prévisualisation (sandbox) : autorisés si explicitement demandé.
if env_bool("ALLOW_ANY_HOST", False):
    ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    # tiers
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    # KEMTA
    "common",
    "apps.accounts",
    "apps.customers",
    "apps.companies",
    "apps.service_requests",
    "apps.projects",
    "apps.construction",
    "apps.evidences",
    "apps.reports",
    "apps.properties",
    "apps.maintenance",
    "apps.btp_catalog",
    "apps.opportunities",
    "apps.applications",
    "apps.subscriptions",
    "apps.payments",
    "apps.notifications",
    "apps.activities",
    "apps.dashboard",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "common.middleware.RequestContextMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

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

# --- Base de données --------------------------------------------------------
def _database_from_url(url: str) -> dict:
    parsed = urlparse(url)
    engine = "django.db.backends.postgresql"
    if parsed.scheme.startswith("sqlite"):
        engine = "django.db.backends.sqlite3"
        name = parsed.path.lstrip("/") or str(BASE_DIR / "db.sqlite3")
        return {"ENGINE": engine, "NAME": name}
    opts: dict = {}
    if parsed.scheme in {"postgres", "postgresql", "psql"}:
        opts = {"sslmode": "prefer"}
    return {
        "ENGINE": engine,
        "NAME": unquote(parsed.path.lstrip("/")),
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname or "",
        "PORT": str(parsed.port or ""),
        "CONN_MAX_AGE": env_int("DB_CONN_MAX_AGE", 60),
        "OPTIONS": opts,
    }


_database_url = env("DATABASE_URL")
if _database_url:
    DATABASES = {"default": _database_from_url(_database_url or "")}
elif env("POSTGRES_HOST"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("POSTGRES_DB", "kemta"),
            "USER": env("POSTGRES_USER", "kemta"),
            "PASSWORD": env("POSTGRES_PASSWORD", "kemta"),
            "HOST": env("POSTGRES_HOST", "localhost"),
            "PORT": env("POSTGRES_PORT", "5432"),
            "CONN_MAX_AGE": env_int("DB_CONN_MAX_AGE", 60),
        }
    }
else:
    # Développement sans Docker : repli SQLite pour ne jamais bloquer un dev.
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": str(BASE_DIR / "db.sqlite3"),
        }
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Cache / Redis ----------------------------------------------------------
REDIS_URL = env("REDIS_URL", "")
CACHES = {
    "default": (
        {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
            "KEY_PREFIX": "kemta",
            "TIMEOUT": 300,
        }
        if REDIS_URL
        else {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "kemta-local",
            "KEY_PREFIX": "kemta",
            "TIMEOUT": 300,
        }
    )
}

SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"

# --- Celery -----------------------------------------------------------------
CELERY_BROKER_URL = env("CELERY_BROKER_URL", REDIS_URL or "memory://")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", REDIS_URL or "cache+memory://")
CELERY_TASK_ALWAYS_EAGER = env_bool("CELERY_TASK_ALWAYS_EAGER", False)
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_TASK_TIME_LIMIT = env_int("CELERY_TASK_TIME_LIMIT", 600)
CELERY_TASK_SOFT_TIME_LIMIT = env_int("CELERY_TASK_SOFT_TIME_LIMIT", 540)
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_MAX_TASKS_PER_CHILD = env_int("CELERY_WORKER_MAX_TASKS_PER_CHILD", 200)
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = "Africa/Douala"
CELERY_BEAT_SCHEDULE = {
    "cleanup-expired-otp": {
        "task": "apps.accounts.tasks.cleanup_expired_otp",
        "schedule": 900.0,  # 15 min
    },
    "billing-run-recurring": {
        "task": "apps.subscriptions.tasks.run_recurring_billing",
        "schedule": 60 * 60 * 6,  # toutes les 6 h
    },
    "maintenance-visit-reminders": {
        "task": "apps.maintenance.tasks.send_visit_reminders",
        "schedule": 60 * 60 * 12,
    },
    "projects-progress-snapshot": {
        "task": "apps.projects.tasks.snapshot_progress",
        "schedule": 60 * 60,
    },
    "notifications-retry-pending": {
        "task": "apps.notifications.tasks.dispatch_pending",
        "schedule": 300.0,
    },
    "projects-flag-at-risk": {
        "task": "apps.projects.tasks.flag_at_risk_projects",
        "schedule": 60 * 60 * 24,  # 1 fois par jour
    },
    "cleanup-unlinked-assets": {
        "task": "common.tasks.cleanup_unlinked_assets",
        "schedule": 60 * 60 * 24 * 7,  # hebdomadaire
    },
}

# --- Authentification -------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = [
    "apps.accounts.backends.PhonePasswordBackend",
    "django.contrib.auth.backends.ModelBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env_int("JWT_ACCESS_MINUTES", 30)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env_int("JWT_REFRESH_DAYS", 14)),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": JWT_SECRET,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "TOKEN_OBTAIN_SERIALIZER": "apps.accounts.serializers.KemtaTokenObtainSerializer",
    "TOKEN_REFRESH_SERIALIZER": "apps.accounts.serializers.KemtaTokenRefreshSerializer",
}

# --- DRF --------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_PAGINATION_CLASS": "common.pagination.KemtaCursorPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_THROTTLE_CLASSES": (
        "common.throttling.SensitiveBurstThrottle",
        "common.throttling.SensitiveSustainedThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "burst": "60/min",
        "sustained": "2000/day",
        "otp_request": "5/hour",
        "otp_verify": "10/hour",
        "login": "10/min",
        "register": "10/hour",
        "public_write": "20/hour",
        "anon": "120/min",
        "user": "6000/day",
    },
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "common.exceptions.kemta_exception_handler",
    "DATETIME_FORMAT": "%Y-%m-%dT%H:%M:%S%z",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "KEMTA API",
    "DESCRIPTION": (
        "API de la plateforme KEMTA : suivi de chantier, entretien immobilier, "
        "espace entreprises BTP, opportunités et paiements. Authentification "
        "principale par numéro de téléphone + code OTP."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": "/api/v1",
}

# --- CORS / CSRF ------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173",
)
CORS_ALLOW_CREDENTIALS = True
CORS_URLS_REGEX = r"^/api/.*$"
if env_bool("CORS_ALLOW_ALL", False):
    CORS_ALLOW_ALL_ORIGINS = True
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", "http://localhost:5173,http://127.0.0.1:8000")
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = "Lax"

# --- Internationalisation ---------------------------------------------------
LANGUAGE_CODE = "fr"
LANGUAGES = [("fr", "Français"), ("en", "English")]
TIME_ZONE = "Africa/Douala"
USE_I18N = True
USE_TZ = True
LOCALE_PATHS = [BASE_DIR / "locale"]

# --- Fichiers statiques / médias -------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# --- Stockage objet (S3 / R2 / MinIO) --------------------------------------
OBJECT_STORAGE_BUCKET = env("OBJECT_STORAGE_BUCKET", "")
OBJECT_STORAGE_ENDPOINT = env("OBJECT_STORAGE_ENDPOINT", "")
OBJECT_STORAGE_REGION = env("OBJECT_STORAGE_REGION", "eu-west-3")
OBJECT_STORAGE_PUBLIC_BASE_URL = env("OBJECT_STORAGE_PUBLIC_BASE_URL", "")
OBJECT_STORAGE_ACCESS_KEY = env("OBJECT_STORAGE_ACCESS_KEY", "")
OBJECT_STORAGE_SECRET_KEY = env("OBJECT_STORAGE_SECRET_KEY", "")
OBJECT_STORAGE_PRESIGN_TTL = env_int("OBJECT_STORAGE_PRESIGN_TTL", 900)
MAX_UPLOAD_BYTES = env_int("MAX_UPLOAD_BYTES", 15 * 1024 * 1024)
IMAGE_MAX_DIMENSION = env_int("IMAGE_MAX_DIMENSION", 2000)

# --- OTP / SMS --------------------------------------------------------------
OTP_LENGTH = env_int("OTP_LENGTH", 6)
OTP_TTL_SECONDS = env_int("OTP_TTL_SECONDS", 300)
OTP_MAX_ATTEMPTS = env_int("OTP_MAX_ATTEMPTS", 5)
OTP_RESEND_COOLDOWN_SECONDS = env_int("OTP_RESEND_COOLDOWN_SECONDS", 45)
OTP_MAX_REQUESTS_PER_WINDOW = env_int("OTP_MAX_REQUESTS_PER_WINDOW", 5)
OTP_WINDOW_SECONDS = env_int("OTP_WINDOW_SECONDS", 3600)
OTP_DEV_ECHO = env_bool("OTP_DEV_ECHO", False)

SMS_PROVIDER = env("SMS_PROVIDER", "console")
SMS_API_KEY = env("SMS_API_KEY", "")
SMS_API_SECRET = env("SMS_API_SECRET", "")
SMS_SENDER_ID = env("SMS_SENDER_ID", "KEMTA")
SMS_BASE_URL = env("SMS_BASE_URL", "")
SMS_TIMEOUT_SECONDS = env_int("SMS_TIMEOUT_SECONDS", 15)

DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "KEMTA <notifications@kemta.cm>")
EMAIL_BACKEND = env("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", "")
EMAIL_PORT = env_int("EMAIL_PORT", 587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
WHATSAPP_ENABLED = env_bool("WHATSAPP_ENABLED", False)

# --- Paiements --------------------------------------------------------------
PAYMENT_PROVIDER = env("PAYMENT_PROVIDER", "manual")
PAYMENT_API_KEY = env("PAYMENT_API_KEY", "")
PAYMENT_BASE_URL = env("PAYMENT_BASE_URL", "")
PAYMENT_TIMEOUT_SECONDS = env_int("PAYMENT_TIMEOUT_SECONDS", 20)
PAYMENT_API_SECRET = env("PAYMENT_API_SECRET", "")
PAYMENT_WEBHOOK_SECRET = env("PAYMENT_WEBHOOK_SECRET", "")
PAYMENT_CURRENCY = env("PAYMENT_CURRENCY", "XAF")
PAYMENT_MIN_AMOUNT_XAF = env_int("PAYMENT_MIN_AMOUNT_XAF", 1000)

# --- Métier -----------------------------------------------------------------
KEMTA_BRAND_NAME = env("KEMTA_BRAND_NAME", "KEMTA SUIVI")
KEMTA_SUPPORT_PHONE = env("KEMTA_SUPPORT_PHONE", "+237600000000")
KEMTA_SUPPORT_EMAIL = env("KEMTA_SUPPORT_EMAIL", "contact@kemta.cm")
KEMTA_REFERENCE_PREFIX = env("KEMTA_REFERENCE_PREFIX", "KEMTA")
KEMTA_OFFER_CURRENCY = "XAF"
DEFAULT_COUNTRY_CODE = env("DEFAULT_COUNTRY_CODE", "CM")

# --- Observabilité ----------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "structured": {
            "()": "common.logging.StructuredFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        },
        "human": {"format": "[%(asctime)s] %(levelname)s %(name)s: %(message)s"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "structured" if env_bool("LOG_JSON", True) else "human",
        },
    },
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", "INFO")},
    "loggers": {
        "django.db.backends": {"level": env("SQL_LOG_LEVEL", "WARNING"), "propagate": True},
        "kemta": {"level": env("LOG_LEVEL", "INFO"), "propagate": True},
    },
}
HEALTH_CHECK_CACHE_KEY = "kemta:health"
