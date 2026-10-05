"""Génération et vérification des codes OTP.

Choix de sécurité :
- le code est généré par ``secrets`` (CSPRNG), jamais ``random`` ;
- stockage d'une empreinte HMAC-SHA256 (clé = SECRET_KEY serveur, sel = 8 octets
  aléatoires par enregistrement). Le code en clair n'existe que dans le SMS ;
- comparaison en temps constant (``hmac.compare_digest``) ;
- un seul code actif par (numéro, usage) : tout nouveau code invalide l'ancien ;
- expiration courte, tentatives limitées, quotas horaires côté Redis, et traçage.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import AuthAuditLog, OTPPurpose, OTPVerification
from common.exceptions import BusinessRuleError
from common.throttling import check_otp_request_quota, otp_cooldown_remaining, set_otp_cooldown
from common.utils import mask_phone, normalize_phone

logger = logging.getLogger("kemta.auth.otp")

TICKET_KEY = "kemta:auth:ticket:{ticket}"
TICKET_TTL = 15 * 60


def generate_code() -> str:
    """Code numérique de ``OTP_LENGTH`` chiffres, sans biais modulo."""
    length = settings.OTP_LENGTH
    upper = 10**length
    return f"{secrets.randbelow(upper):0{length}d}"


def hash_code(code: str, salt: str) -> str:
    material = f"{salt}:{code}".encode("utf-8")
    key = settings.SECRET_KEY.encode("utf-8")
    return hmac.new(key, material, hashlib.sha256).hexdigest()


def verify_code(code: str, salt: str, expected_hash: str) -> bool:
    if not code or not salt or not expected_hash:
        return False
    candidate = hash_code(str(code).strip(), salt)
    return hmac.compare_digest(candidate, expected_hash)


def client_ip(request) -> str | None:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()[:45]
    return request.META.get("REMOTE_ADDR")


@transaction.atomic
def issue_otp(
    *,
    phone: str,
    purpose: str,
    request=None,
    enforce_cooldown: bool = True,
    user=None,
) -> OTPVerification:
    """Crée un nouveau code OTP et programme son envoi par SMS (Celery)."""
    normalized = normalize_phone(phone)
    ip = client_ip(request) if request is not None else None

    if enforce_cooldown:
        remaining = otp_cooldown_remaining(normalized, purpose)
        if remaining > 0:
            AuthAuditLog.objects.create(
                phone=normalized, event=AuthAuditLog.Event.OTP_THROTTLED,
                success=False, ip_address=ip, detail=f"cooldown actif ({remaining}s)",
            )
            raise BusinessRuleError(
                f"Un code vient de vous être envoyé. Vous pourrez en demander un nouveau "
                f"dans {remaining} seconde{'s' if remaining > 1 else ''}."
            )

    allowed, wait = check_otp_request_quota(normalized)
    if not allowed:
        AuthAuditLog.objects.create(
            phone=normalized, event=AuthAuditLog.Event.OTP_THROTTLED, success=False, ip_address=ip,
            detail="quota horaire atteint",
        )
        raise BusinessRuleError(
            "Trop de demandes de code ont été effectuées pour ce numéro. "
            f"Merci de réessayer dans {max(1, wait // 60)} minute(s) ou de contacter le support KEMTA."
        )

    previous_active = OTPVerification.invalidate_active(normalized, purpose)
    resend_count = 0
    if previous_active:
        last = (
            OTPVerification.objects.filter(phone=normalized, purpose=purpose)
            .order_by("-created_at")
            .values_list("resend_count", flat=True)
            .first()
        )
        resend_count = min((last or 0) + 1, 99)

    code = generate_code()
    otp = OTPVerification(
        phone=normalized,
        purpose=purpose,
        expires_at=timezone.now() + timedelta(seconds=settings.OTP_TTL_SECONDS),
        max_attempts=settings.OTP_MAX_ATTEMPTS,
        resend_count=resend_count,
        ip_address=ip,
        user_agent=(request.META.get("HTTP_USER_AGENT", "")[:255] if request is not None else ""),
        user=user,
    )
    otp.set_code(code)
    otp.save()
    _store_dev_echo(normalized, purpose, code)

    set_otp_cooldown(normalized, purpose)

    AuthAuditLog.objects.create(
        phone=normalized, event=AuthAuditLog.Event.OTP_REQUESTED, user=user, ip_address=ip,
        user_agent=otp.user_agent, detail=f"purpose={purpose}, resend={resend_count}",
    )

    # L'envoi SMS ne bloque jamais la requête HTTP.
    from apps.accounts.tasks import send_otp_sms

    payload = {
        "phone": normalized,
        "code": code,
        "purpose": purpose,
        "ttl_minutes": max(1, settings.OTP_TTL_SECONDS // 60),
    }
    if settings.CELERY_TASK_ALWAYS_EAGER:
        send_otp_sms.apply(kwargs=payload, throw=False)
    else:
        transaction.on_commit(lambda: send_otp_sms.delay(**payload))

    logger.info("otp_issued", extra={"phone": mask_phone(normalized), "purpose": purpose})
    return otp


def confirm_otp(*, phone: str, purpose: str, code: str, request=None, user=None) -> str:
    """Valide un code et renvoie un ticket d'échange à usage unique."""
    normalized = normalize_phone(phone)
    ip = client_ip(request) if request is not None else None

    otp = (
        OTPVerification.objects.filter(phone=normalized, purpose=purpose)
        .order_by("-created_at")
        .first()
    )
    if otp is None:
        raise BusinessRuleError(
            "Aucun code en attente pour ce numéro. Demandez d'abord un nouveau code."
        )

    if otp.used_at:
        raise BusinessRuleError(
            "Ce code a déjà été utilisé. Demandez-en un nouveau pour continuer."
        )
    if otp.invalidated_at:
        raise BusinessRuleError(
            "Ce code a été remplacé par un nouveau. Utilisez le dernier SMS reçu."
        )
    if otp.is_expired:
        AuthAuditLog.objects.create(
            phone=normalized, event=AuthAuditLog.Event.OTP_EXPIRED, success=False, ip_address=ip
        )
        raise BusinessRuleError(
            "Ce code a expiré (validité 5 minutes). Demandez un nouveau code."
        )
    if otp.attempts >= otp.max_attempts:
        AuthAuditLog.objects.create(
            phone=normalized, event=AuthAuditLog.Event.OTP_FAILED, success=False, ip_address=ip,
            detail="tentatives épuisées",
        )
        raise BusinessRuleError(
            "Trop de tentatives sur ce code. Demandez un nouveau code, il remplacera celui-ci."
        )

    if not otp.matches(code):
        otp.register_failure()
        AuthAuditLog.objects.create(
            phone=normalized, event=AuthAuditLog.Event.OTP_FAILED, success=False, ip_address=ip,
            detail=f"tentative {otp.attempts}/{otp.max_attempts}",
        )
        remaining = max(0, otp.max_attempts - otp.attempts)
        raise BusinessRuleError(
            "Le code saisi n'est pas correct."
            + (f" Il vous reste {remaining} tentative(s)." if remaining else
               " Demandez un nouveau code.")
        )

    otp.consume()
    AuthAuditLog.objects.create(
        phone=normalized, event=AuthAuditLog.Event.OTP_VERIFIED, user=user or otp.user, ip_address=ip
    )

    ticket = secrets.token_urlsafe(32)
    cache.set(
        TICKET_KEY.format(ticket=ticket),
        {"phone": normalized, "purpose": purpose, "verified_at": timezone.now().isoformat()},
        TICKET_TTL,
    )
    logger.info("otp_confirmed", extra={"phone": mask_phone(normalized), "purpose": purpose})
    return ticket


def consume_ticket(*, ticket: str, phone: str, purpose: str) -> bool:
    """Échange un ticket contre l'autorisation d'une action (usage unique)."""
    key = TICKET_KEY.format(ticket=ticket or "")
    payload = cache.get(key)
    if not payload:
        return False
    if payload.get("phone") != normalize_phone(phone) or payload.get("purpose") != purpose:
        return False
    cache.delete(key)  # usage unique : jamais rejouable
    return True


DEV_ECHO_KEY = "kemta:otp:dev:{phone}:{purpose}"


def _store_dev_echo(phone: str, purpose: str, code: str) -> None:
    """En développement uniquement, garde le code lisible pour les tests E2E.

    En production, ``OTP_DEV_ECHO`` est faux et rien n'est conservé : le code
    n'existe alors que dans le SMS.
    """
    if settings.OTP_DEV_ECHO and settings.DEBUG:
        cache.set(DEV_ECHO_KEY.format(phone=phone, purpose=purpose), code, settings.OTP_TTL_SECONDS)


def dev_echo_code(phone: str, purpose: str) -> str:
    if not (settings.OTP_DEV_ECHO and settings.DEBUG):
        return ""
    return cache.get(DEV_ECHO_KEY.format(phone=normalize_phone(phone), purpose=purpose), "")


def dev_echo_enabled() -> bool:
    return bool(settings.OTP_DEV_ECHO and settings.DEBUG)
