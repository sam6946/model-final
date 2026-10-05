"""Réglages de production : sécurité durcie, HTTPS, PostgreSQL, Redis."""
from .base import *  # noqa: F401,F403
from .base import REDIS_URL, SECRET_KEY, env, env_bool, env_int, env_list

DEBUG = False

if not SECRET_KEY or SECRET_KEY == "dev-only-secret-change-me":  # noqa: F405
    raise RuntimeError("SECRET_KEY doit être défini en production (.env).")

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "kemta.cm,www.kemta.cm,api.kemta.cm")

# --- Sécurité de transport --------------------------------------------------
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
SECURE_HSTS_SECONDS = env_int("SECURE_HSTS_SECONDS", 60 * 60 * 24 * 180)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = "Lax"
LANGUAGE_COOKIE_SECURE = True

CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", "https://kemta.cm,https://www.kemta.cm")

# --- Exploitation -----------------------------------------------------------
LOG_JSON = env_bool("LOG_JSON", True)
LOG_LEVEL = env("LOG_LEVEL", "INFO")
CELERY_TASK_ALWAYS_EAGER = False
OTP_DEV_ECHO = False

# Le cache Redis est obligatoire en production : le repli locmem casserait les
# compteurs de débit, les tickets OTP et les permissions partagées entre workers.
if not REDIS_URL:
    raise RuntimeError("REDIS_URL doit être défini en production.")

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
        "KEY_PREFIX": "kemta",
        "IGNORE_EXCEPTIONS": False,
    }
}
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14
