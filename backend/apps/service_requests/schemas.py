"""Validation des formulaires dynamiques de demande de service.

Chaque service possède ses propres champs obligatoires. La validation vit ici
(et non dans le serializer générique) pour que les règles métier restent au même
endroit quel que soit le canal d'entrée (site, téléphone, back-office).
"""
from __future__ import annotations

from datetime import date

from rest_framework import serializers

from apps.service_requests.models import ServiceKind
from common.utils import parse_amount, today_or_none

MAINTENANCE_SERVICE_CHOICES = [
    "nettoyage", "jardinage", "plomberie", "electricite", "peinture",
    "inspection", "petites_reparations", "autre",
]

FREQUENCY_CHOICES = ["PUNCTUAL", "MONTHLY", "QUARTERLY", "SEMIANNUAL", "ON_DEMAND"]

PROGRESS_CHOICES = [
    "FONDATIONS", "ELEVATION", "DALLAGE", "TOITURE", "FINITIONS", "ACHEVE", "AUTRE",
]


def _clean_choice(value, choices: list[str], field_label: str, *, allow_empty: bool = True) -> str:
    if not value:
        if allow_empty:
            return ""
        raise serializers.ValidationError(f"Veuillez préciser {field_label}.")
    if str(value) not in choices:
        raise serializers.ValidationError(f"La valeur choisie pour {field_label} n'est pas reconnue.")
    return str(value)


def validate_payload_for_kind(kind: str, payload: dict, data: dict) -> dict:
    """Valide et normalise les réponses selon le service demandé."""
    payload = dict(payload or {})
    errors: dict[str, list[str]] = {}

    def require(field: str, message: str) -> None:
        if not data.get(field):
            errors.setdefault(field, []).append(message)

    if kind == ServiceKind.BUILD_PROJECT:
        require("project_type", "Veuillez indiquer le type de projet (villa, immeuble, local…).")
        require("location_text", "Veuillez renseigner la localisation prévue du projet.")
        require("budget_max_xaf", "Veuillez indiquer votre budget approximatif, même estimatif.")
        payload["has_land"] = bool(payload.get("has_land"))
        payload["has_plan"] = bool(payload.get("has_plan"))
        payload["land_status"] = _clean_choice(
            payload.get("land_status"), ["TITLED", "BOUGHT_NOT_TITLED", "FAMILY", "LOOKING", "NONE"],
            "la situation du terrain", allow_empty=True,
        )

    elif kind == ServiceKind.EXISTING_SITE:
        require("location_text", "Veuillez renseigner la localisation du chantier.")
        require("current_progress", "Veuillez indiquer le niveau d'avancement actuel.")
        data["current_progress"] = _clean_choice(
            data.get("current_progress"), PROGRESS_CHOICES, "le niveau d'avancement", allow_empty=False
        )
        payload["needs_audit"] = bool(payload.get("needs_audit", True))
        payload["wants_takeover"] = bool(payload.get("wants_takeover", False))

    elif kind == ServiceKind.MAINTENANCE:
        require("property_type", "Veuillez préciser le type de propriété.")
        require("location_text", "Veuillez renseigner la localisation de la propriété.")
        services = data.get("maintenance_services") or []
        if not services:
            errors.setdefault("maintenance_services", []).append(
                "Sélectionnez au moins une prestation souhaitée."
            )
        invalid = [item for item in services if item not in MAINTENANCE_SERVICE_CHOICES]
        if invalid:
            errors.setdefault("maintenance_services", []).append(
                "Une des prestations sélectionnées n'est pas reconnue."
            )
        data["maintenance_frequency"] = _clean_choice(
            data.get("maintenance_frequency"), FREQUENCY_CHOICES, "la fréquence souhaitée"
        )
        data["property_occupied"] = _clean_choice(
            data.get("property_occupied"),
            ["VACANT", "OCCUPIED_OWNER", "RENTED", "FAMILY", "GUARDED", "UNKNOWN"],
            "l'occupation de la propriété",
        )
        last_visit = today_or_none(str(data.get("last_visit_date") or ""))
        if last_visit and last_visit > date.today():
            errors.setdefault("last_visit_date", []).append(
                "La date de dernière visite ne peut pas être dans le futur."
            )
        data["last_visit_date"] = last_visit

    else:  # AUTRE
        require("description", "Décrivez votre besoin en quelques lignes pour que nous puissions vous aider.")

    # Règles communes
    budget_min = parse_amount(data.get("budget_min_xaf"))
    budget_max = parse_amount(data.get("budget_max_xaf"))
    if budget_min and budget_max and budget_min > budget_max:
        errors.setdefault("budget_max_xaf", []).append(
            "Le budget maximum doit être supérieur au budget minimum."
        )
    data["budget_min_xaf"] = budget_min
    data["budget_max_xaf"] = budget_max
    data["spent_xaf"] = parse_amount(data.get("spent_xaf"))
    data["desired_start_date"] = today_or_none(str(data.get("desired_start_date") or ""))

    if errors:
        raise serializers.ValidationError(errors)
    return payload
