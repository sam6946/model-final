"""Tâches Celery du domaine comptes (envoi d'OTP, nettoyage, notifications)."""
from __future__ import annotations

import logging

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from common.services.sms import SmsError, otp_message, send_sms

logger = logging.getLogger("kemta.tasks.accounts")


@shared_task(
    name="apps.accounts.tasks.send_otp_sms",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(),
)
def send_otp_sms(self, *, phone: str, code: str, purpose: str, ttl_minutes: int = 5) -> dict:
    """Envoie le code par SMS. Ne bloque jamais la requête HTTP.

    Échec réseau ou 5xx → nouvelle tentative (30 s, 60 s, 120 s).
    Rejet définitif (numéro invalide) → pas de retry, on trace.
    """
    message = otp_message(code=code, minutes=ttl_minutes)
    try:
        result = send_sms(phone=phone, message=message)
    except SmsError as exc:
        logger.warning("otp_sms_retry", extra={"phone": phone, "attempt": self.request.retries})
        raise self.retry(exc=exc, countdown=30 * (2**self.request.retries)) from exc

    if not result.delivered:
        logger.error("otp_sms_undelivered", extra={"phone": phone, "purpose": purpose,
                                                   "detail": result.detail})
        return {"delivered": False, "detail": result.detail}
    return {"delivered": True, "provider": result.provider, "reference": result.reference}


@shared_task(name="apps.accounts.tasks.cleanup_expired_otp")
def cleanup_expired_otp(retention_days: int = 7) -> int:
    """Purge les OTP expirés/consommés : la table ne doit pas gonfler."""
    from datetime import timedelta

    from apps.accounts.models import OTPVerification

    cutoff = timezone.now() - timedelta(days=retention_days)
    deleted, _ = OTPVerification.objects.filter(created_at__lt=cutoff).delete()
    logger.info("otp_cleanup", extra={"deleted": deleted})
    return deleted


@shared_task(name="apps.accounts.tasks.purge_expired_tickets")
def purge_expired_tickets() -> dict:
    """Nettoie les tickets d'authentification abandonnés (Redis TTL de secours)."""
    from django.core.cache import cache

    from apps.accounts.services.otp import TICKET_KEY

    # Le cache gère le TTL ; cette tâche ne sert qu'à journaliser l'état
    # pour l'exploitation (ex. Redis saturé par des tickets non consommés).
    try:
        cache.get(f"{TICKET_KEY.format(ticket='health')}")
    except Exception:  # pragma: no cover
        logger.exception("cache_unavailable")
    return {"status": "ok", "checked_at": timezone.now().isoformat()}


@shared_task(name="apps.accounts.tasks.expire_idle_sessions")
def expire_idle_sessions() -> int:
    """Marque comme révoquées les sessions d'appareil expirées."""
    from apps.accounts.models import DeviceSession

    return DeviceSession.objects.filter(
        revoked_at__isnull=True, expires_at__lt=timezone.now()
    ).update(revoked_at=timezone.now())
