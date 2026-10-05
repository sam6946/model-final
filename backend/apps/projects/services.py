"""Services métier des projets : création, planning, avancement, rapports.

Toute la logique vit ici (les vues ne font que valider/orchestrer), ce qui
permet de réutiliser exactement le même comportement depuis :

- le back-office KEMTA (conversion d'une demande),
- une tâche Celery (snapshot d'avancement, génération de rapport),
- les tests.
"""
from __future__ import annotations

import logging
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone

from apps.activities.services import record_activity
from apps.construction.models import Phase, PhaseStatus, PhaseTemplate
from apps.notifications.services import notify
from apps.projects.models import (
    BudgetLine,
    HealthStatus,
    Project,
    ProjectKind,
    ProjectMember,
    ProjectStatus,
    ProjectUpdate,
    Task,
)
from common.constants import NotificationType
from common.utils import humanize_amount

logger = logging.getLogger("kemta.projects")

# Squelette de phases par défaut pour une construction neuve.
DEFAULT_BUILD_PHASES = [
    {"name": "Étude, plans et autorisations", "weight_percent": 6, "duration_days": 30},
    {"name": "Installation de chantier et implantations", "weight_percent": 5, "duration_days": 10},
    {"name": "Terrassement et fondations", "weight_percent": 18, "duration_days": 30},
    {"name": "Élévation et structure", "weight_percent": 24, "duration_days": 60},
    {"name": "Dallage et planchers", "weight_percent": 10, "duration_days": 25},
    {"name": "Charpente et toiture", "weight_percent": 12, "duration_days": 30},
    {"name": "Menuiserie et fermetures", "weight_percent": 8, "duration_days": 25},
    {"name": "Électricité et plomberie", "weight_percent": 9, "duration_days": 30},
    {"name": "Finitions et peinture", "weight_percent": 6, "duration_days": 30},
    {"name": "Réception et levée des réserves", "weight_percent": 2, "duration_days": 15},
]

DEFAULT_FOLLOW_UP_PHASES = [
    {"name": "Audit d'entrée et état des lieux", "weight_percent": 10, "duration_days": 10},
    {"name": "Reprise technique des travaux", "weight_percent": 40, "duration_days": 60},
    {"name": "Finitions et second œuvre", "weight_percent": 40, "duration_days": 45},
    {"name": "Réception technique", "weight_percent": 10, "duration_days": 10},
]


def phases_for_kind(kind: str) -> list[dict]:
    if kind == ProjectKind.FOLLOW_UP:
        return DEFAULT_FOLLOW_UP_PHASES
    if kind == ProjectKind.MAINTENANCE:
        return [
            {"name": "Diagnostic complet du bien", "weight_percent": 25, "duration_days": 7},
            {"name": "Travaux de remise en état", "weight_percent": 60, "duration_days": 30},
            {"name": "Contrôle final et rapport", "weight_percent": 15, "duration_days": 5},
        ]
    return DEFAULT_BUILD_PHASES


@transaction.atomic
def create_project_from_request(*, service_request, actor, overrides: dict | None = None) -> Project:
    """Crée un projet à partir d'une demande qualifiée, avec ses phases et son budget.

    Le client est automatiquement ajouté comme observateur, le chargé de suivi
    reçoit une notification, et les indicateurs sont initialisés à partir des
    informations saisies (budget, dates, localisation).
    """
    from apps.service_requests.models import RequestStatus, ServiceKind, ServiceRequestEvent

    overrides = overrides or {}
    kind_map = {
        ServiceKind.BUILD_PROJECT: ProjectKind.BUILD,
        ServiceKind.EXISTING_SITE: ProjectKind.FOLLOW_UP,
        ServiceKind.MAINTENANCE: ProjectKind.MAINTENANCE,
        ServiceKind.OTHER: ProjectKind.STUDY,
    }
    kind = overrides.get("kind") or kind_map.get(service_request.kind, ProjectKind.BUILD)

    customer = service_request.customer
    if customer is None and service_request.phone:
        from django.contrib.auth import get_user_model

        User = get_user_model()
        customer = User.objects.filter(phone=service_request.phone).first()

    name = overrides.get("name") or _default_project_name(service_request)
    manager = overrides.get("manager") or overrides.get("manager_id") or actor
    manager_id = getattr(manager, "pk", manager)
    company_id = overrides.get("company") or overrides.get("company_id")
    company_id = getattr(company_id, "pk", company_id)
    project = Project.objects.create(
        name=name,
        kind=kind,
        customer=customer or actor,  # repli : le dossier reste pilotable
        request=service_request,
        manager_id=manager_id,
        company_id=company_id,
        location=service_request.location,
        location_text=overrides.get("location_text") or service_request.location_text,
        address=overrides.get("address", ""),
        description=service_request.description,
        status=overrides.get("status") or ProjectStatus.PLANNING,
        health=overrides.get("health") or HealthStatus.ON_TRACK,
        planned_start=overrides.get("planned_start") or service_request.desired_start_date,
        planned_end=overrides.get("planned_end"),
        actual_start=overrides.get("actual_start"),
        budget_total_xaf=overrides.get("budget_total_xaf") or service_request.budget_max_xaf,
        budget_spent_xaf=service_request.spent_xaf or Decimal("0"),
        contract_signed=bool(overrides.get("contract_signed", False)),
    )

    # Phases : squelette fonction de la nature du projet.
    template = PhaseTemplate.objects.filter(kind=kind, is_active=True).first()
    if template:
        template.apply_to(project, start_date=project.planned_start)
    else:
        _create_default_phases(project)

    # Équipe : client en lecture + chargé de suivi.
    if project.customer_id:
        ProjectMember.objects.get_or_create(
            project=project,
            user=project.customer,
            defaults={"role": ProjectMember.MemberRole.CLIENT_PROXY, "can_view_finance": True},
        )
    if project.manager_id:
        ProjectMember.objects.get_or_create(
            project=project,
            user=project.manager,
            defaults={
                "role": ProjectMember.MemberRole.MANAGER,
                "can_validate_evidence": True,
                "can_view_finance": True,
                "can_manage_schedule": True,
            },
        )

    # Lignes budgétaires de base, réparties selon le budget connu.
    if project.budget_total_xaf:
        _seed_budget_lines(project)

    previous_status = service_request.status
    service_request.converted_project = project
    service_request.status = RequestStatus.CONVERTED
    service_request.save(update_fields=["converted_project", "status", "updated_at"])
    ServiceRequestEvent.objects.create(
        request=service_request,
        actor=actor,
        from_status=previous_status,
        to_status=RequestStatus.CONVERTED,
        comment=f"Projet {project.reference} ouvert : {project.name}",
        is_customer_visible=True,
    )

    # Le journal du projet démarre dès l'ouverture : le client doit voir sa première
    # entrée dans le fil chronologique, même avant tout travaux.
    ProjectUpdate.objects.create(
        project=project,
        author=actor,
        update_type=ProjectUpdate.UpdateType.MILESTONE,
        message=(
            f"Projet ouvert par KEMTA à partir de la demande {service_request.reference}. "
            f"Nature : {project.get_kind_display()}. Un chargé de suivi prend contact pour "
            "planifier le démarrage des travaux."
        ),
        payload={
            "reference": project.reference,
            "request_reference": service_request.reference,
            "planned_start": project.planned_start.isoformat() if project.planned_start else None,
            "budget_total_xaf": str(project.budget_total_xaf or ""),
        },
        visibility="CUSTOMER",
    )

    record_activity(
        verb="PROJECT_CREATED",
        message=f"Projet {project.reference} créé ({project.get_kind_display()})",
        actor=actor,
        project=project,
        entity_type="Project",
        entity_id=project.pk,
        url=f"/admin/projets/{project.pk}",
        visibility="CUSTOMER",
        is_important=True,
    )

    if project.customer_id:
        notify(
            recipient=project.customer,
            notification_type=NotificationType.PROJECT,
            title="Votre projet est ouvert sur KEMTA",
            body=(
                f"Le dossier {project.reference} « {project.name} » est créé. "
                "Vous recevrez chaque mise à jour et pourrez suivre l'avancement en photos."
            ),
            action_url=f"/espace/projets/{project.pk}",
            action_label="Voir mon projet",
            entity_type="Project",
            entity_id=project.pk,
            project=project,
            payload={"reference": project.reference, "project_name": project.name},
            dedupe_key=f"project:{project.pk}:created",
        )
    logger.info("project_created", extra={"reference": project.reference, "kind": project.kind})
    return project


def _default_project_name(service_request) -> str:
    label = {
        "VILLA": "Villa",
        "IMMEUBLE": "Immeuble",
        "APPARTEMENT": "Résidence",
        "MAISON": "Maison",
        "LOCAL_COMMERCIAL": "Local commercial",
        "ECOLE": "Établissement scolaire",
    }.get((service_request.project_type or "").upper(), "Projet immobilier")
    location = service_request.location_text or service_request.city or "Cameroun"
    return f"{label} — {location}"[:200]


def _create_default_phases(project: Project) -> list[Phase]:
    start = project.planned_start or timezone.localdate()
    cursor = start
    created: list[Phase] = []
    for index, step in enumerate(phases_for_kind(project.kind)):
        duration = int(step["duration_days"])
        created.append(
            Phase.objects.create(
                project=project,
                name=step["name"],
                order=index,
                weight_percent=Decimal(str(step["weight_percent"])),
                planned_start=cursor,
                planned_end=cursor + timedelta(days=duration),
                status=PhaseStatus.NOT_STARTED,
            )
        )
        cursor += timedelta(days=duration)
    if not project.planned_end and created:
        Project.objects.filter(pk=project.pk).update(planned_end=created[-1].planned_end)
        project.planned_end = created[-1].planned_end
    return created


def _seed_budget_lines(project: Project) -> list[BudgetLine]:
    """Répartit le budget connu en lignes types (ajustables par le chargé de suivi)."""
    total = project.budget_total_xaf or Decimal("0")
    if not total:
        return []
    shares = [
        (BudgetLine.Category.MATERIAUX, "Matériaux de construction", Decimal("0.45")),
        (BudgetLine.Category.MAIN_OEUVRE, "Main-d'œuvre et tâcherons", Decimal("0.30")),
        (BudgetLine.Category.TRANSPORT, "Transport et logistique", Decimal("0.08")),
        (BudgetLine.Category.LOCATION, "Location de matériel", Decimal("0.05")),
        (BudgetLine.Category.ETUDES, "Études, plans et honoraires", Decimal("0.07")),
        (BudgetLine.Category.ADMINISTRATIF, "Frais administratifs et autorisations", Decimal("0.05")),
    ]
    created: list[BudgetLine] = []
    for category, label, ratio in shares:
        created.append(
            BudgetLine.objects.create(
                project=project,
                category=category,
                label=label,
                planned_xaf=(total * ratio).quantize(Decimal("1")),
            )
        )
    return created


@transaction.atomic
def update_progress(
    *, project: Project, progress: float | None = None, actor=None, note: str = "", notify_client: bool = True
) -> Project:
    """Met à jour l'avancement global, la santé et informe le client."""
    from decimal import Decimal as D

    if progress is not None:
        project.physical_progress = D(str(round(max(0.0, min(100.0, progress)), 2)))
        if project.physical_progress >= 100 and project.status != ProjectStatus.COMPLETED:
            project.status = ProjectStatus.COMPLETED
            project.actual_end = project.actual_end or timezone.localdate()
            project.health = HealthStatus.COMPLETED
        elif project.physical_progress > 0 and project.status in {ProjectStatus.DRAFT, ProjectStatus.PLANNING}:
            project.status = ProjectStatus.IN_PROGRESS
            project.actual_start = project.actual_start or timezone.localdate()
        project.save(update_fields=[
            "physical_progress", "status", "actual_end", "actual_start", "health", "updated_at",
        ])

    project.refresh_health()
    project.recalculate_finance()

    message = note or f"Avancement du chantier : {project.physical_progress:.0f} %"
    project.log_update(
        author=actor,
        message=message,
        update_type="PROGRESS",
        payload={"progress": float(project.physical_progress), "health": project.health, "status": project.status},
    )
    record_activity(
        verb="PROJECT_UPDATED",
        message=f"{project.reference} : {message}",
        actor=actor,
        project=project,
        entity_type="Project",
        entity_id=project.pk,
        visibility="CUSTOMER",
        payload={"progress": float(project.physical_progress)},
    )
    if notify_client and project.customer_id:
        notify(
            recipient=project.customer,
            notification_type=NotificationType.PROJECT,
            title=f"Avancement mis à jour — {project.name}",
            body=(
                f"{message}. Budget consommé : {project.budget_used_percent:.0f} %."
            ),
            action_url=f"/espace/projets/{project.pk}",
            action_label="Voir le détail",
            entity_type="Project",
            entity_id=project.pk,
            project=project,
            payload={
                "reference": project.reference,
                "project_name": project.name,
                "amount_label": humanize_amount(project.budget_spent_xaf),
            },
            dedupe_key=f"project:{project.pk}:progress:{project.physical_progress:.0f}",
            also_sms=project.health in {HealthStatus.AT_RISK, HealthStatus.WATCH},
        )
    return project


def project_overview_payload(project: Project) -> dict:
    """Vue d'ensemble d'un projet, en un minimum de requêtes.

    Toutes les relations nécessaires sont préchargées par l'appelant
    (``select_related`` / ``prefetch_related``) : pas de N+1.
    """
    phases = list(project.phases.all())
    tasks = project.tasks.all()
    evidences = list(project.evidences.all()[:24])
    today = timezone.localdate()
    return {
        "metrics": {
            "physical_progress": float(project.physical_progress),
            "budget_total_xaf": float(project.budget_total_xaf or 0),
            "budget_spent_xaf": float(project.budget_spent_xaf or 0),
            "budget_used_percent": project.budget_used_percent,
            "budget_remaining_xaf": float(project.budget_remaining_xaf),
            "is_over_budget": project.is_over_budget,
            "is_late": project.is_late,
            "health": project.health,
            "health_label": project.get_health_display(),
            "days_to_deadline": (project.planned_end - today).days if project.planned_end else None,
            "phases_count": len(phases),
            "phases_done": sum(1 for phase in phases if phase.status == PhaseStatus.DONE),
            "phases_blocked": sum(1 for phase in phases if phase.status == PhaseStatus.BLOCKED),
            "tasks_open": sum(1 for task in tasks if task.status in {Task.Status.TODO, Task.Status.IN_PROGRESS}),
            "tasks_overdue": sum(1 for task in tasks if task.is_overdue),
            "evidences_count": project.evidences.count(),
            "evidences_pending": project.evidences.filter(status="PENDING").count(),
        },
        "phases": phases,
        "recent_evidences": evidences,
    }


def portfolio_summary(*, user) -> dict:
    """Synthèse du portefeuille de projets d'un client (une requête agrégée)."""
    queryset = Project.objects.filter(Q(customer=user) | Q(members__user=user)).distinct()
    aggregates = queryset.aggregate(
        total=Count("id"),
        active=Count("id", filter=Q(status__in=[ProjectStatus.PLANNING, ProjectStatus.IN_PROGRESS,
                                                ProjectStatus.HANDOVER, ProjectStatus.ON_HOLD])),
        completed=Count("id", filter=Q(status=ProjectStatus.COMPLETED)),
        at_risk=Count("id", filter=Q(health=HealthStatus.AT_RISK)),
        budget_total=Sum("budget_total_xaf"),
        budget_spent=Sum("budget_spent_xaf"),
    )
    return {
        "projects_total": aggregates["total"] or 0,
        "projects_active": aggregates["active"] or 0,
        "projects_completed": aggregates["completed"] or 0,
        "projects_at_risk": aggregates["at_risk"] or 0,
        "budget_total_xaf": float(aggregates["budget_total"] or 0),
        "budget_spent_xaf": float(aggregates["budget_spent"] or 0),
    }


def create_task(*, project: Project, data: dict, actor) -> Task:
    task = Task.objects.create(
        project=project,
        phase_id=data.get("phase_id"),
        title=data["title"],
        description=data.get("description", ""),
        assignee_id=data.get("assignee_id"),
        priority=data.get("priority") or Task.Priority.NORMAL,
        due_date=data.get("due_date"),
        requires_evidence=bool(data.get("requires_evidence", False)),
        order=data.get("order", 0),
        created_by=actor,
    )
    record_activity(
        verb="TASK_CREATED",
        message=f"Tâche « {task.title} » ajoutée à {project.reference}",
        actor=actor,
        project=project,
        entity_type="Task",
        entity_id=task.pk,
        visibility="CUSTOMER",
    )
    if task.assignee_id and task.assignee_id != getattr(actor, "pk", None):
        notify(
            recipient=task.assignee,
            notification_type=NotificationType.TASK,
            title="Nouvelle tâche assignée",
            body=f"{task.title} — projet {project.reference}",
            action_url=f"/admin/projets/{project.pk}",
            action_label="Ouvrir la tâche",
            entity_type="Task",
            entity_id=task.pk,
            project=project,
            dedupe_key=f"task:{task.pk}:assigned",
            also_sms=task.priority in {Task.Priority.HIGH, Task.Priority.URGENT},
        )
    return task
