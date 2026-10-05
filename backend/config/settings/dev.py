"""Réglages de développement local (SQLite/Redis optionnel, OTP affiché).

Objectif : un développeur clone le dépôt et lance l'application sans Docker,
sans PostgreSQL et sans passerelle SMS.
"""
from .base import *  # noqa: F401,F403
from .base import BASE_DIR, env, env_bool

DEBUG = True
ALLOWED_HOSTS = ["*"]
CORS_ALLOW_ALL_ORIGINS = True

# Cookies non sécurisés en développement (http local).
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# En développement, l'OTP est journalisé / affiché afin de tester le parcours
# complet sans dépendre d'une passerelle SMS réelle.
OTP_DEV_ECHO = env_bool("OTP_DEV_ECHO", True)
SMS_PROVIDER = env("SMS_PROVIDER", "console")

# Celery s'exécute en direct (synchrone) : aucune infrastructure requise.
CELERY_TASK_ALWAYS_EAGER = env_bool("CELERY_TASK_ALWAYS_EAGER", True)

# Repli SQLite si aucune base PostgreSQL n'est configurée.
if not env("DATABASE_URL") and not env("POSTGRES_HOST"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": str(BASE_DIR / "db.sqlite3"),
        }
    }

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"

INTERNAL_IPS = ["127.0.0.1"]
LOG_JSON = False

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
