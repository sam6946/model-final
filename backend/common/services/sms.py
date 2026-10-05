"""Passerelle SMS : abstraction fournisseur (aucun couplage à un opérateur).

En production camerounaise, on peut brancher au choix un agrégateur local
(MTN / Orange, via API partenaires) ou un fournisseur international.
Changer de fournisseur = changer ``SMS_PROVIDER`` dans .env, sans toucher au code.

Les identifiants restent côté serveur : ils ne sont jamais exposés au frontend.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import requests
from django.conf import settings

logger = logging.getLogger("kemta.sms")


class SmsError(Exception):
    """Échec d'envoi : le message sera retenté par Celery."""


@dataclass(frozen=True)
class SmsResult:
    delivered: bool
    provider: str
    reference: str = ""
    detail: str = ""


class SMSProvider:
    """Interface commune à tous les fournisseurs SMS."""

    name = "base"

    def send(self, *, phone: str, message: str) -> SmsResult:
        raise NotImplementedError


class ConsoleSMSProvider(SMSProvider):
    """Développement / tests : le message est journalisé, rien n'est envoyé."""

    name = "console"

    def send(self, *, phone: str, message: str) -> SmsResult:
        logger.info("sms_console", extra={"phone": phone, "sms_body": message})
        print(f"\n[KEMTA SMS -> {phone}] {message}\n")  # noqa: T201 - retour dev explicite
        return SmsResult(delivered=True, provider=self.name, detail="console")


class HttpSMSProvider(SMSProvider):
    """Fournisseur HTTP générique (JSON) : agrégateur local ou international.

    Contrat simple et configurable par .env :
    ``POST {SMS_BASE_URL}/messages`` avec ``{to, sender, message}`` et un Bearer.
    """

    name = "http"

    def __init__(self) -> None:
        if not settings.SMS_BASE_URL or not settings.SMS_API_KEY:
            raise SmsError("Configuration SMS incomplète (SMS_BASE_URL / SMS_API_KEY).")

    def _post(self, url: str, headers: dict, payload: dict) -> SmsResult:
        try:
            response = requests.post(
                url, json=payload, headers=headers, timeout=settings.SMS_TIMEOUT_SECONDS
            )
        except requests.RequestException as exc:
            raise SmsError(f"Réseau SMS indisponible : {exc}") from exc

        if response.status_code >= 500:
            raise SmsError(f"Fournisseur SMS en erreur ({response.status_code}).")
        if response.status_code >= 400:
            # Erreur définitive (numéro invalide, crédit épuisé) : inutile de
            # retenter trois fois et de gaspiller le crédit SMS.
            logger.error(
                "sms_rejected",
                extra={"status": response.status_code, "body": response.text[:300]},
            )
            return SmsResult(delivered=False, provider=self.name, detail=f"HTTP {response.status_code}")
        try:
            data = response.json()
        except ValueError:
            data = {}
        return SmsResult(
            delivered=True,
            provider=self.name,
            reference=str(data.get("id") or data.get("message_id") or ""),
        )

    def send(self, *, phone: str, message: str) -> SmsResult:
        url = f"{settings.SMS_BASE_URL.rstrip('/')}/messages"
        headers = {
            "Authorization": f"Bearer {settings.SMS_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        return self._post(url, headers, {"to": phone, "sender": settings.SMS_SENDER_ID, "message": message})


class OrangeCMMessagingProvider(HttpSMSProvider):
    """Adaptateur Orange Cameroun (SMS API partenaire)."""

    name = "orange_cm"

    def send(self, *, phone: str, message: str) -> SmsResult:
        url = f"{settings.SMS_BASE_URL.rstrip('/')}/smsmessaging/v1/outbound"
        headers = {
            "Authorization": f"Bearer {settings.SMS_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "outboundSMSMessageRequest": {
                "address": f"tel:{phone}",
                "senderAddress": f"tel:{settings.SMS_SENDER_ID}",
                "outboundSMSTextMessage": {"message": message},
            }
        }
        return self._post(url, headers, payload)


class MTNSMSProvider(HttpSMSProvider):
    """Adaptateur MTN Cameroun (SMS API partenaire)."""

    name = "mtn_cm"

    def send(self, *, phone: str, message: str) -> SmsResult:
        url = f"{settings.SMS_BASE_URL.rstrip('/')}/sms/send"
        headers = {"X-API-Key": settings.SMS_API_KEY, "Content-Type": "application/json"}
        payload = {"msisdn": phone.lstrip("+"), "text": message, "from": settings.SMS_SENDER_ID}
        return self._post(url, headers, payload)


PROVIDERS: dict[str, type[SMSProvider]] = {
    "console": ConsoleSMSProvider,
    "http": HttpSMSProvider,
    "orange_cm": OrangeCMMessagingProvider,
    "mtn_cm": MTNSMSProvider,
    "twilio": HttpSMSProvider,
    "vonage": HttpSMSProvider,
}


def get_sms_provider() -> SMSProvider:
    provider_key = (settings.SMS_PROVIDER or "console").strip().lower()
    provider_class = PROVIDERS.get(provider_key, ConsoleSMSProvider)
    try:
        return provider_class()
    except SmsError:
        # Repli explicite : mieux vaut tracer en console que perdre un OTP.
        logger.error("sms_provider_fallback_console", extra={"provider": provider_key})
        return ConsoleSMSProvider()


def send_sms(*, phone: str, message: str) -> SmsResult:
    provider = get_sms_provider()
    result = provider.send(phone=phone, message=message)
    if not result.delivered:
        logger.warning(
            "sms_not_delivered", extra={"provider": result.provider, "detail": result.detail}
        )
    return result


OTP_TEMPLATE = (
    "{brand} : votre code de verification est {code}. "
    "Valable {minutes} minutes. Ne le partagez avec personne."
)


def otp_message(*, code: str, minutes: int = 5) -> str:
    return OTP_TEMPLATE.format(
        brand=settings.KEMTA_BRAND_NAME.split()[0], code=code, minutes=minutes
    )
