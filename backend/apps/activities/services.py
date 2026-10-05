"""Écriture du journal d'activité et de l'audit de sécurité."""
from __future__ import annotations

import logging

from django.db import transaction

from apps.activities.models import ActivityLog, ActivityVerb, AuditLog

logger = logging.getLogger("kemta.activity")


@transaction.atomic
def record_activity(
    *,
    verb: str,
    message: str = "",
    actor=None,
    project=None,
    company=None,
    property=None,
    entity_type: str = "",
    entity_id: int | None = None,
    url: str = "",
    payload: dict | None = None,
    visibility: str = "TEAM",
    is_important: bool = False,
) -> ActivityLog:
    """Enregistre un événement affichable dans un fil d'activité.

    Les appels proviennent des vues et des services ; en cas d'échec (base
    indisponible, contrainte), on journalise sans casser l'action métier :
    l'activité est une trace, jamais un point de blocage.
    """
    try:
        return ActivityLog.objects.create(
            actor=actor if getattr(actor, "pk", None) else None,
            verb=verb,
            message=message[:255],
            project=project,
            company=company,
            property=property,
            entity_type=entity_type[:40],
            entity_id=entity_id,
            url=url[:255],
            payload=payload or {},
            visibility=visibility,
            is_important=is_important,
        )
    except Exception:  # pragma: no cover - la trace ne doit jamais bloquer
        logger.exception("activity_record_failed", extra={"verb": verb})
        return ActivityLog(verb=verb, message=message[:255])


@transaction.atomic
def record_audit(
    *,
    action: str,
    user=None,
    entity_type: str = "",
    entity_id: str | int = "",
    description: str = "",
    changes: dict | None = None,
    request=None,
    status_code: int | None = None,
    duration_ms: int | None = None,
) -> AuditLog:
    """Journalise une action sensible (sécurité, conformité, litiges)."""
    ip = None
    user_agent = ""
    path = ""
    method = ""
    trace_id = ""
    if request is not None:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        ip = (forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR")) or None
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:255]
        path = request.path[:255]
        method = request.method[:10]
        trace_id = getattr(request, "trace_id", "")[:40]
    try:
        return AuditLog.objects.create(
            user=user if getattr(user, "pk", None) else None,
            action=action,
            entity_type=entity_type[:60],
            entity_id=str(entity_id)[:60],
            description=description[:255],
            changes=changes or {},
            path=path,
            method=method,
            status_code=status_code,
            ip_address=ip,
            user_agent=user_agent,
            trace_id=trace_id,
            duration_ms=duration_ms,
        )
    except Exception:  # pragma: no cover
        logger.exception("audit_record_failed", extra={"action": action})
        return AuditLog(action=action)


def diff_changes(before: dict, after: dict) -> dict:
    """Calcule les champs modifiés, en masquant les valeurs sensibles."""
    sensitive = {"password", "code", "code_hash", "salt", "token", "refresh", "access"}
    changes: dict[str, dict] = {}
    for key, new_value in after.items():
        if key in sensitive:
            changes[key] = {"changed": True}
            continue
        old_value = before.get(key)
        if old_value != new_value:
            changes[key] = {"from": _safe(old_value), "to": _safe(new_value)}
    return changes


def _safe(value):
    if isinstance(value, (int, float, bool, type(None), str)):
        return value if not isinstance(value, str) or len(value) < 200 else value[:200] + "…"
    return str(value)[:200]
