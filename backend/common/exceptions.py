"""Gestion d'erreurs homogène : réponses lisibles en français, jamais de fuite.

Contrat d'erreur de l'API KEMTA :
{
  "error": {"code": "otp_invalid", "message": "...", "fields": {...}}
}
Le frontend affiche ``message`` tel quel : chaque message doit être humain.
"""
from __future__ import annotations

import logging
import uuid

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import APIException, ErrorDetail, NotFound, Throttled, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger("kemta.api")


class BusinessRuleError(APIException):
    """Règle métier non respectée (ex. plan insuffisant, candidature fermée)."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "Cette action n'est pas possible dans l'état actuel du dossier."
    default_code = "business_rule"

    def __init__(self, detail=None, code=None) -> None:
        super().__init__(detail, code)


class PermissionCodeError(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "Vous n'avez pas l'autorisation d'effectuer cette action."
    default_code = "permission_denied"


class RateLimitedError(Throttled):
    default_detail = (
        "Trop de tentatives en peu de temps. Merci de patienter quelques minutes "
        "avant de réessayer."
    )


class ServiceUnavailableError(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Le service est momentanément indisponible. Merci de réessayer dans un instant."
    default_code = "service_unavailable"


FIELD_LABELS = {
    "phone": "le numéro de téléphone",
    "code": "le code de vérification",
    "password": "le mot de passe",
    "password_confirm": "la confirmation du mot de passe",
    "first_name": "le prénom",
    "last_name": "le nom",
    "email": "l'adresse e-mail",
    "city": "la ville",
    "terms_accepted": "l'acceptation des conditions",
    "budget": "le budget",
}


def human_message(code: str, field: str | None = None, detail: str | None = None) -> str:
    """Traduit un code technique en message compréhensible par un client."""
    label = FIELD_LABELS.get(field or "", f"le champ « {field} »" if field else "")
    messages = {
        "required": f"Veuillez renseigner {label}.",
        "blank": f"Veuillez renseigner {label}.",
        "invalid": f"La valeur saisie pour {label} n'est pas valide.",
        "invalid_phone": "Ce numéro de téléphone n'est pas valide. Exemple : +237 6 99 11 22 33.",
        "invalid_code": "Le code saisi n'est pas correct. Vérifiez les 6 chiffres reçus par SMS.",
        "expired_code": "Ce code a expiré. Demandez-en un nouveau.",
        "exists": "Ce numéro est déjà associé à un compte KEMTA. Connectez-vous plutôt.",
        "phone_taken": "Ce numéro est déjà associé à un compte KEMTA. Connectez-vous plutôt.",
        "email_taken": "Cette adresse e-mail est déjà utilisée par un autre compte.",
        "password_too_short": "Choisissez un mot de passe d'au moins 8 caractères.",
        "password_too_common": "Ce mot de passe est trop simple. Ajoutez des chiffres et des lettres.",
        "password_mismatch": "Les deux mots de passe ne correspondent pas.",
        "too_many_attempts": "Trop de tentatives sur ce code. Demandez un nouveau code.",
        "cooldown": "Vous venez de recevoir un code. Patientez quelques secondes avant d'en demander un nouveau.",
        "quota": "Trop de demandes de code pour ce numéro. Réessayez dans une heure.",
        "not_verified": "Votre numéro n'est pas encore vérifié. Validez le code reçu par SMS.",
        "terms_required": "Vous devez accepter les conditions d'utilisation pour continuer.",
        "idempotent_replay": "Cette action a déjà été enregistrée, elle n'a pas été répétée.",
    }
    return detail or messages.get(code, "Les informations transmises sont incomplètes ou invalides.")


def _flatten(errors, field: str | None = None) -> dict[str, list[str]]:
    flat: dict[str, list[str]] = {}
    if isinstance(errors, dict):
        for key, value in errors.items():
            flat.update(_flatten(value, key if key != "non_field_errors" else field))
    elif isinstance(errors, (list, tuple)):
        for item in errors:
            flat.update(_flatten(item, field))
    else:
        code = getattr(errors, "code", "invalid")
        text = human_message(code, field, str(errors) if code not in {
            "required", "blank", "invalid", "invalid_phone", "exists", "password_too_short",
            "password_too_common", "terms_required", "invalid_code", "expired_code",
        } else None)
        flat.setdefault(field or "detail", []).append(text)
    return flat


def kemta_exception_handler(exc, context) -> Response | None:
    """Adapte toutes les erreurs à un format unique et lisible."""
    request = context.get("request")
    trace_id = getattr(request, "trace_id", None) or uuid.uuid4().hex[:12]
    view = context.get("view")
    view_name = f"{view.__class__.__module__}.{view.__class__.__name__}" if view else "?"

    if isinstance(exc, DjangoValidationError):
        exc = ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
    elif isinstance(exc, (ObjectDoesNotExist,)):
        exc = NotFound(detail=human_message("invalid", None, "Cette ressource n'existe pas ou a été supprimée."))
    elif isinstance(exc, Http404):
        exc = NotFound(detail=human_message("invalid", None, "Cette ressource n'existe pas ou a été supprimée."))
    elif isinstance(exc, IntegrityError):
        logger.warning("integrity_error", extra={"view": view_name, "trace_id": trace_id})
        return Response(
            {
                "error": {
                    "code": "conflict",
                    "message": "Cet enregistrement existe déjà ou entre en conflit avec une donnée existante.",
                    "trace_id": trace_id,
                }
            },
            status=status.HTTP_409_CONFLICT,
        )

    response = drf_exception_handler(exc, context)
    if response is None:
        logger.exception("unhandled_exception", extra={"view": view_name, "trace_id": trace_id})
        return Response(
            {
                "error": {
                    "code": "server_error",
                    "message": "Une erreur interne est survenue. Notre équipe technique est informée.",
                    "trace_id": trace_id,
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    detail = response.data
    code = getattr(exc, "default_code", "error")
    fields: dict[str, list[str]] = {}
    message = ""

    if isinstance(detail, dict) and "detail" in detail and len(detail) == 1:
        message = str(detail["detail"])
        code = getattr(detail["detail"], "code", code)
    elif isinstance(detail, (list, str, ErrorDetail)):
        message = str(detail[0] if isinstance(detail, list) and detail else detail)
    else:
        fields = _flatten(detail)
        first_field = next(iter(fields), None)
        message = fields[first_field][0] if first_field else "Les informations transmises ne sont pas valides."

    if isinstance(exc, Throttled):
        code = "rate_limited"
        wait = getattr(exc, "wait", None)
        if wait:
            minutes = int(wait // 60)
            seconds = int(wait % 60)
            delay = f"{minutes} min" if minutes else f"{seconds} s"
            message = f"Trop de tentatives. Veuillez réessayer dans {delay}."
        else:
            message = human_message("quota")
    if isinstance(exc, PermissionDenied) or response.status_code == 403:
        code = code if code not in ("permission_denied", "error") else "forbidden"
        message = message or "Vous n'avez pas l'autorisation d'accéder à cette ressource."
    if response.status_code == 404 and not message:
        message = "Cette ressource n'existe pas ou a été supprimée."
    if response.status_code >= 500:
        logger.error(
            "api_error_5xx",
            extra={"view": view_name, "trace_id": trace_id, "status": response.status_code},
        )

    payload = {
        "error": {
            "code": code,
            "message": message,
            "fields": fields,
            "trace_id": trace_id,
        }
    }
    response.data = payload
    response["X-Trace-Id"] = trace_id
    return response
