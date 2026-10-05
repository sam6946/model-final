"""Services des preuves terrain : création idempotente, validation, notifications."""
from __future__ import annotations

import logging
import uuid

from django.db import transaction

from apps.activities.services import record_activity
from apps.evidences.models import Evidence, EvidenceStatus
from apps.notifications.services import notify
from apps.projects.models import Project
from common.constants import NotificationType

logger = logging.getLogger("kemta.evidences")


@transaction.atomic
def create_evidence(*, data: dict, actor) -> Evidence:
    """Crée une preuve (ou renvoie l'existante si le client rejoue l'envoi)."""
    client_uuid = data.get("client_uuid")
    if client_uuid:
        existing = Evidence.objects.filter(client_uuid=client_uuid).first()
        if existing is not None:
            return existing  # synchronisation hors ligne rejouée : aucune duplication

    project = None
    if data.get("project"):
        project = Project.objects.filter(pk=data["project"]).only("id").first()
    evidence = Evidence.objects.create(
        project_id=data.get("project"),
        property_id=data.get("property"),
        phase_id=data.get("phase"),
        task_id=data.get("task"),
        kind=data.get("kind") or "PHOTO",
        title=(data.get("title") or "")[:180],
        caption=(data.get("caption") or "")[:255],
        note=data.get("note") or "",
        asset_id=data.get("asset"),
        measurements=data.get("measurements") or {},
        captured_at=data.get("captured_at"),
        captured_by=actor,
        capture_device=(data.get("capture_device") or "")[:120],
        latitude=data.get("latitude"),
        longitude=data.get("longitude"),
        accuracy_meters=data.get("accuracy_meters"),
        is_offline_capture=bool(data.get("is_offline_capture")),
        client_uuid=client_uuid or uuid.uuid4(),
        uploaded_by=actor,
    )
    evidence.compute_distance_to_site()

    if project is not None:
        project.log_update(
            author=actor,
            message=f"Nouvelle preuve terrain : {evidence.title or evidence.get_kind_display()}",
            update_type="EVIDENCE",
            payload={
                "evidence_id": evidence.pk,
                "kind": evidence.kind,
                "thumbnail_url": evidence.thumbnail_url,
                "phase": evidence.phase_id,
            },
        )
    record_activity(
        verb="EVIDENCE_UPLOADED",
        message=f"Preuve déposée sur {project.reference if project else 'une propriété'}",
        actor=actor,
        project=project,
        entity_type="Evidence",
        entity_id=evidence.pk,
        visibility="TEAM",
        payload={"kind": evidence.kind, "suspect_location": evidence.is_location_suspect},
    )

    # Contrôle qualité : les managers du projet arbitrent avant publication client.
    if project is not None:
        from django.contrib.auth import get_user_model

        User = get_user_model()
        validators = set()
        if project.manager_id:
            validators.add(project.manager_id)
        validators.update(
            project.members.filter(can_validate_evidence=True, removed_at__isnull=True).values_list("user_id", flat=True)
        )
        validators.update(User.objects.filter(role__in=["ADMIN", "MANAGER"], is_active=True).values_list("id", flat=True))
        for user_id in validators - {actor.pk}:
            recipient = User.objects.filter(pk=user_id).first()
            if recipient is None:
                continue
            notify(
                recipient=recipient,
                notification_type=NotificationType.EVIDENCE,
                title="Preuve à valider",
                body=(
                    f"{actor.full_name} a déposé une preuve sur {project.reference}. "
                    "Validez-la pour la publier au client."
                ),
                action_url=f"/admin/projets/{project.pk}",
                action_label="Valider la preuve",
                entity_type="Evidence",
                entity_id=evidence.pk,
                project=project,
                dedupe_key=f"evidence:{evidence.pk}:review:{recipient.pk}",
            )
    return evidence


def review_evidence(*, evidence: Evidence, action: str, reviewer, comment: str = "") -> Evidence:
    """Valide ou refuse une preuve ; le client n'est prévenu que sur validation."""
    if action == "validate":
        evidence.validate_by(reviewer, comment=comment)
        record_activity(
            verb="EVIDENCE_VALIDATED",
            message=f"Preuve validée sur {evidence.project.reference if evidence.project_id else 'une propriété'}",
            actor=reviewer,
            project=evidence.project,
            entity_type="Evidence",
            entity_id=evidence.pk,
            visibility="CUSTOMER",
        )
        _notify_client_validated(evidence)
    else:
        evidence.reject_by(reviewer, reason=comment)
        record_activity(
            verb="EVIDENCE_REJECTED",
            message=f"Preuve refusée : {comment[:120]}",
            actor=reviewer,
            project=evidence.project,
            entity_type="Evidence",
            entity_id=evidence.pk,
            visibility="TEAM",
        )
        if evidence.captured_by_id and evidence.captured_by_id != reviewer.pk:
            notify(
                recipient=evidence.captured_by,
                notification_type=NotificationType.EVIDENCE,
                title="Preuve refusée — action attendue",
                body=f"Motif : {comment}. Merci de reprendre la photo ou d'ajouter une précision.",
                action_url=f"/terrain/preuves/{evidence.pk}",
                action_label="Corriger",
                entity_type="Evidence",
                entity_id=evidence.pk,
                project=evidence.project,
                dedupe_key=f"evidence:{evidence.pk}:rejected",
            )
    return evidence


def _notify_client_validated(evidence: Evidence) -> None:
    project = evidence.project
    if project is None or not project.customer_id:
        return
    notify(
        recipient=project.customer,
        notification_type=NotificationType.EVIDENCE,
        title=f"Nouvelle preuve photo — {project.name}",
        body=(
            f"{evidence.title or evidence.get_kind_display()} : "
            f"{evidence.caption or evidence.note or 'photo du chantier'} "
            f"({evidence.freshness_label})"
        ),
        action_url=f"/espace/projets/{project.pk}",
        action_label="Voir la preuve",
        entity_type="Evidence",
        entity_id=evidence.pk,
        project=project,
        payload={
            "reference": project.reference,
            "project_name": project.name,
            "thumbnail_url": evidence.thumbnail_url,
        },
        dedupe_key=f"evidence:{evidence.pk}:published",
    )


def sync_offline_batch(*, items: list[dict], actor) -> dict:
    """Traite un lot de preuves synchronisées depuis la PWA terrain.

    Idempotent : le terrain peut rejouer le même lot (réseau coupé, batterie
    faible, double appui sur « Synchroniser ») sans jamais créer de doublon.
    Le ``client_uuid`` généré sur l'appareil fait office de clé d'unicité.
    """
    created, replayed, failed = [], 0, []
    for item in items:
        data = dict(item)
        client_uuid = data.get("client_uuid")
        try:
            if client_uuid and Evidence.objects.filter(client_uuid=client_uuid).exists():
                replayed += 1
                continue
            evidence = create_evidence(data=data, actor=actor)
            created.append(evidence)
        except Exception as exc:
            logger.warning(
                "offline_sync_item_failed",
                extra={"error": str(exc), "client_uuid": str(client_uuid or "")},
            )
            failed.append({"client_uuid": str(client_uuid or ""), "error": str(exc)[:140]})

    return {
        "created": len(created),
        "replayed": replayed,
        "failed": failed,
        "pending_validation": sum(
            1 for evidence in created if evidence.status == EvidenceStatus.PENDING
        ),
        "references": [str(evidence.client_uuid) for evidence in created],
    }
