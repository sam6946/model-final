"""Réglages de test : rapides, isolés, sans dépendance externe."""
from .base import *  # noqa: F401,F403
from .base import BASE_DIR

DEBUG = False
ALLOWED_HOSTS = ["*"]
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "kemta-test"}
}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
CELERY_TASK_ALWAYS_EAGER = True
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
OTP_DEV_ECHO = True
SMS_PROVIDER = "console"
MEDIA_ROOT = BASE_DIR / "test-media"
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
# Les tests ne doivent jamais être limités par les throttles.
REST_FRAMEWORK = {**REST_FRAMEWORK, "DEFAULT_THROTTLE_RATES": {  # noqa: F405
    "burst": "10000/min",
    "sustained": "100000/day",
    "otp_request": "10000/hour",
    "otp_verify": "10000/hour",
    "login": "10000/min",
    "register": "10000/hour",
    "public_write": "10000/hour",
    "anon": "10000/min",
    "user": "100000/day",
}}
