"""Tâches planifiées du suivi de projet.

Deux responsabilités, exécutées par Celery beat :

1. `snapshot_progress` — figer l'avancement et la consommation budgétaire de
   chaque projet actif. Le client voit alors une courbe réelle (dérive de
   planning, accélération de dépenses) et non une photo instantanée.
2. `flag_at_risk_projects` — repérer les projets en retard ou en dépassement et
   alerter le chargé de suivi *avant* que le client ne découvre le problème.
"""
from __future__ import annotations

import logging
from datetime import timedelta
from decimal import Decimal

from celery import shared_task
from django.utils import timezone

from apps.notifications.services import notify
from apps.projects.models import Project, ProjectStatus, ProjectUpdate
from common.constants import NotificationType

logger = logging.getLogger("kemta.projects")

ACTIVE_STATUSES = [
    ProjectStatus.PLANNING,
    ProjectStatus.IN_PROGRESS,
    ProjectStatus.ON_HOLD,
]

# Au-delà de ces seuils, un projet est considéré « à risque ».
BUDGET_ALERT_RATIO = Decimal("0.90")   # 90 % du budget consommé
PROGRESS_ALERT_GAP = Decimal("25")     # 25 points de décalage délai / avancement


@shared_task(name="apps.projects.tasks.snapshot_progress")
def snapshot_progress(limit: int = 500) -> dict:
    """Enregistre un jalon d'avancement pour chaque projet actif.

    Un unique enregistrement par jour et par projet : la tâche est rejouable
    sans dupliquer l'historique (contrainte d'idempotence par date).
    """
    today = timezone.localdate()
    created = 0
    skipped = 0

    projects = (
        Project.objects.filter(status__in=ACTIVE_STATUSES, is_archived=False)
        .select_related("manager")
        .order_by("id")[:limit]
    )

    for project in projects:
        already = ProjectUpdate.objects.filter(
            project=project,
            update_type=ProjectUpdate.UpdateType.PROGRESS,
            created_at__date=today,
        ).exists()
        if already:
            skipped += 1
            continue

        spent = project.budget_spent_xaf
        ProjectUpdate.objects.create(
            project=project,
            update_type=ProjectUpdate.UpdateType.PROGRESS,
            visibility="TEAM",
            message=(
                f"Jalon automatique du {today:%d/%m/%Y} : avancement "
                f"{project.physical_progress} %, budget consommé "
                f"{project.budget_used_percent} %."
            ),
            payload={
                "physical_progress": float(project.physical_progress or 0),
                "budget_used_percent": float(project.budget_used_percent or 0),
                "budget_spent_xaf": float(spent or 0),
                "source": "snapshot_progress",
            },
        )
        created += 1

    if created:
        logger.info("project_snapshots_created", extra={"count": created})
    return {"created": created, "skipped": skipped, "date": today.isoformat()}


@shared_task(name="apps.projects.tasks.flag_at_risk_projects")
def flag_at_risk_projects(limit: int = 200) -> dict:
    """Alerte les chargés de suivi sur les projets en dérive.

    Règles métier :
      · projet en retard sur son échéance planifiée, ou
      · budget consommé ≥ 90 % alors que l'avancement est inférieur de plus de
        15 points, ou
      · projet sans mise à jour client depuis 14 jours (chantier silencieux).
    """
    now = timezone.now()
    today = timezone.localdate()
    silence_threshold = now - timedelta(days=14)
    flagged = 0
    details: list[dict] = []

    candidates = (
        Project.objects.filter(status__in=ACTIVE_STATUSES, is_archived=False)
        .select_related("manager", "customer")
        .order_by("id")[:limit]
    )

    for project in candidates:
        reasons: list[str] = []

        if project.planned_end and project.planned_end < today and (project.physical_progress or 0) < 100:
            reasons.append("Échéance dépassée sans réception")

        spent_ratio = Decimal(str(project.budget_used_percent or 0)) / 100
        progress_ratio = Decimal(str(project.physical_progress or 0)) / 100
        if spent_ratio >= BUDGET_ALERT_RATIO and (spent_ratio - progress_ratio) >= Decimal("0.15"):
            reasons.append("Budget consommé très en avance sur l'avancement réel")

        last_customer_update = (
            ProjectUpdate.objects.filter(project=project, visibility="CUSTOMER")
            .order_by("-created_at")
            .values_list("created_at", flat=True)
            .first()
        )
        if last_customer_update is None or last_customer_update < silence_threshold:
            reasons.append("Aucune information client publiée depuis 14 jours")

        if not reasons:
            continue

        recipients = [user for user in (project.manager, project.customer) if user is not None]
        for recipient in recipients:
            notify(
                recipient=recipient,
                notification_type=NotificationType.PROJECT,
                title=f"Attention requise — {project.reference}",
                body=(
                    f"{project.name} : " + " · ".join(reasons) + ". "
                    "Vérifiez le dossier et informez le client."
                ),
                action_url=f"/espace/projets/{project.pk}",
                action_label="Ouvrir le projet",
                project=project,
                entity_type="project",
                entity_id=project.pk,
                dedupe_key=f"project-risk-{project.pk}-{recipient.pk}-{today.isoformat()}",
                payload={"project_id": project.pk, "reference": project.reference, "reasons": reasons},
            )

        flagged += 1
        details.append({"project": project.reference, "reasons": reasons})

    if flagged:
        logger.warning("projects_at_risk", extra={"count": flagged})
    return {"flagged": flagged, "details": details[:20]}
