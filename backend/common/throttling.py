"""Limitation de débit : Redis si disponible, sinon cache local.

Protège en priorité l'envoi d'OTP (coût SMS + surface d'attaque brute force).
"""
from __future__ import annotations

import logging
import time

from django.core.cache import cache
from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle, UserRateThrottle

logger = logging.getLogger("kemta.throttle")


class _RedisReadyThrottle(SimpleRateThrottle):
    """Base : horodatages stockés en cache (Redis en production)."""

    def get_cache_key(self, request, view) -> str | None:
        return None

    def throttle_success(self) -> bool:
        self.history.insert(0, self.now)
        cache.set(self.key, self.history, self.timeout_window)
        return True

    def throttle_failure(self) -> bool:
        # On n'allonge pas la fenêtre à chaque tentative refusée : sinon un
        # attaquant peut bloquer indéfiniment un numéro légitime (déni de
        # service sur les OTP). La fenêtre glisse naturellement.
        logger.warning(
            "rate_limited",
            extra={"scope": getattr(self, "scope", "?"), "ident": self.key},
        )
        return False

    @property
    def timeout_window(self) -> int:
        return int(self.duration)

    def allow_request(self, request, view) -> bool:
        if getattr(view, "throttle_scope_disabled", False):
            return True
        if self.rate is None:
            return True
        try:
            self.key = self.get_cache_key(request, view)
        except Exception:  # le cache ne doit jamais faire échouer une requête
            logger.warning("throttle_key_failed", exc_info=True)
            return True
        if self.key is None:
            return True
        self.history = cache.get(self.key, [])
        self.now = self.timer()
        while self.history and self.history[-1] <= self.now - self.duration:
            self.history.pop()
        if len(self.history) >= self.num_requests:
            return self.throttle_failure()
        return self.throttle_success()


class SensitiveBurstThrottle(_RedisReadyThrottle):
    scope = "burst"

    def get_cache_key(self, request, view) -> str:
        ident = request.user.pk if getattr(request, "user", None) and request.user.is_authenticated else self.get_ident(request)
        return f"kemta:thr:burst:{ident}"


class SensitiveSustainedThrottle(_RedisReadyThrottle):
    scope = "sustained"

    def get_cache_key(self, request, view) -> str:
        ident = request.user.pk if getattr(request, "user", None) and request.user.is_authenticated else self.get_ident(request)
        return f"kemta:thr:sustained:{ident}"


class OTPRequestThrottle(_RedisReadyThrottle):
    scope = "otp_request"

    def get_cache_key(self, request, view) -> str:
        return f"kemta:thr:otp_req:{self.phone_key(request)}"

    @staticmethod
    def phone_key(request) -> str:
        """Clé de débit : le numéro normalisé, sinon l'adresse IP."""
        from common.utils import normalize_phone

        raw = str((request.data or {}).get("phone") or "")
        try:
            return normalize_phone(raw)
        except ValueError:
            return f"ip:{request.META.get('REMOTE_ADDR', 'unknown')}"


class OTPVerifyThrottle(_RedisReadyThrottle):
    scope = "otp_verify"

    def get_cache_key(self, request, view) -> str:
        from common.utils import normalize_phone

        raw = (request.data or {}).get("phone") or ""
        try:
            phone = normalize_phone(raw)
        except ValueError:
            phone = request.META.get("REMOTE_ADDR", "unknown")
        return f"kemta:thr:otp_ver:{phone}"


class LoginThrottle(_RedisReadyThrottle):
    """Freine le bourrage d'identifiants : clé = téléphone + IP."""

    scope = "login"

    def get_cache_key(self, request, view) -> str:
        from common.utils import normalize_phone

        raw = (request.data or {}).get("phone") or ""
        try:
            phone = normalize_phone(raw)
        except ValueError:
            phone = "anon"
        return f"kemta:thr:login:{phone}:{self.get_ident(request)}"


class RegisterThrottle(_RedisReadyThrottle):
    scope = "register"

    def get_cache_key(self, request, view) -> str:
        return f"kemta:thr:register:{self.get_ident(request)}"


class PublicWriteThrottle(_RedisReadyThrottle):
    """Protège les formulaires publics (demande de service, candidature)."""

    scope = "public_write"

    def get_cache_key(self, request, view) -> str:
        ident = request.user.pk if getattr(request, "user", None) and request.user.is_authenticated else self.get_ident(request)
        return f"kemta:thr:public:{ident}"


class AnonThrottle(AnonRateThrottle):
    scope = "anon"


class UserScopedThrottle(UserRateThrottle):
    scope = "user"


def check_otp_request_quota(phone: str) -> tuple[bool, int]:
    """Quota glissant d'envois d'OTP par numéro (anti-SMS bombing).

    Renvoie ``(autorisé, secondes_restantes)``.
    """
    from django.conf import settings

    key = f"kemta:otp:quota:{phone}"
    window = settings.OTP_WINDOW_SECONDS
    limit = settings.OTP_MAX_REQUESTS_PER_WINDOW
    now = int(time.time())
    history: list[int] = cache.get(key, [])
    history = [stamp for stamp in history if stamp > now - window]
    if len(history) >= limit:
        return False, max(0, window - (now - history[0]))
    history.append(now)
    cache.set(key, history, window)
    return True, 0


def otp_cooldown_remaining(phone: str, purpose: str) -> int:
    """Secondes restantes avant de pouvoir renvoyer un code.

    L'échéance est stockée explicitement dans la valeur (et non déduite du TTL) :
    `cache.ttl()` n'existe ni dans le backend Redis de Django ni dans le cache
    mémoire utilisé en développement ou en test. Le comportement reste identique
    quel que soit le cache configuré.
    """
    key = _cooldown_key(phone, purpose)
    deadline = cache.get(key)
    if not deadline:
        return 0
    try:
        remaining = int(float(deadline) - time.time())
    except (TypeError, ValueError):
        # Valeur écrite par une version antérieure du code : on considère la
        # période de refroidissement comme encore active.
        return get_otp_cooldown_seconds()
    return max(0, remaining)


def set_otp_cooldown(phone: str, purpose: str) -> None:
    """Arme le délai de refroidissement après un envoi de code."""
    seconds = get_otp_cooldown_seconds()
    cache.set(_cooldown_key(phone, purpose), time.time() + seconds, seconds)


def _cooldown_key(phone: str, purpose: str) -> str:
    return f"kemta:otp:cooldown:{phone}:{purpose}"


def get_otp_cooldown_seconds() -> int:
    from django.conf import settings

    return int(getattr(settings, "OTP_RESEND_COOLDOWN_SECONDS", 45))
