"""Services d'entretien : création de contrat, planification, alertes."""
from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone

from apps.activities.services import record_activity
from apps.maintenance.models import MaintenanceContract, MaintenanceVisit
from apps.notifications.services import notify
from apps.properties.models import Property
from common.constants import NotificationType

logger = logging.getLogger("kemta.maintenance")


@transaction.atomic
def create_contract(*, data: dict, customer, actor) -> MaintenanceContract:
    """Ouvre un contrat d'entretien et planifie immédiatement les visites."""
    prop = Property.objects.filter(pk=data["property"]).first()
    if prop is None:
        raise ValueError("La propriété indiquée est introuvable.")

    contract = MaintenanceContract.objects.create(
        property=prop,
        customer=customer,
        frequency=data["frequency"],
        start_date=data.get("start_date") or timezone.localdate(),
        end_date=data.get("end_date"),
        price_xaf=data.get("price_xaf"),
        billing_cycle_months=data.get("billing_cycle_months", 1),
        visits_included=data.get("visits_included", 1),
        assigned_team_id=data.get("assigned_team"),
        instructions=data.get("instructions", ""),
        auto_generate_visits=data.get("auto_generate_visits", True),
        status=MaintenanceContract.Status.ACTIVE,
        created_by=actor,
    )
    service_ids = data.get("service_ids") or []
    if service_ids:
        contract.services.set(service_ids)

    visits = contract.generate_next_visits(count=contract.visits_included or 1)
    # Le prochain passage doit être annoncé au client : c'est la valeur perçue.
    if visits:
        next_visit = visits[0]
        notify(
            recipient=customer,
            notification_type=NotificationType.MAINTENANCE,
            title=f"Entretien planifié — {prop.name}",
            body=(
                f"Votre contrat {contract.reference} est actif. Première visite prévue le "
                f"{timezone.localtime(next_visit.scheduled_for).strftime('%d/%m/%Y à %H:%M')}."
            ),
            action_url=f"/espace/proprietes/{prop.pk}",
            action_label="Voir le planning",
            entity_type="MaintenanceContract",
            entity_id=contract.pk,
            payload={"reference": contract.reference},
            dedupe_key=f"contract:{contract.pk}:created",
            also_sms=True,
        )

    record_activity(
        verb="VISIT_SCHEDULED",
        message=f"Contrat d'entretien {contract.reference} ouvert pour {prop.name}",
        actor=actor,
        property=prop,
        entity_type="MaintenanceContract",
        entity_id=contract.pk,
        visibility="CUSTOMER",
        is_important=True,
    )
    propagation_service_ids = list(contract.services.values_list("id", flat=True))
    logger.info(
        "maintenance_contract_created",
        extra={"reference": contract.reference, "services": len(propagation_service_ids)},
    )
    return contract


def complete_visit(*, visit: MaintenanceVisit, actor, report: str = "", score: int | None = None) -> MaintenanceVisit:
    """Clôture une visite, met à jour l'état du bien et informe le client."""
    visit.complete(report=report, score=score, actor=actor)
    prop = visit.property
    owner = prop.owner
    notify(
        recipient=owner,
        notification_type=NotificationType.MAINTENANCE,
        title=f"Visite réalisée — {prop.name}",
        body=(
            f"Visite {visit.reference} effectuée. "
            f"{'État constaté : ' + str(visit.condition_score) + '/100. ' if visit.condition_score else ''}"
            f"{visit.customer_visible_report or report}"[:280]
        ),
        action_url=f"/espace/proprietes/{prop.pk}",
        action_label="Voir le compte rendu",
        entity_type="MaintenanceVisit",
        entity_id=visit.pk,
        payload={"reference": visit.reference},
        dedupe_key=f"visit:{visit.pk}:done",
    )
    record_activity(
        verb="VISIT_COMPLETED",
        message=f"Visite {visit.reference} réalisée sur {prop.name}",
        actor=actor,
        property=prop,
        entity_type="MaintenanceVisit",
        entity_id=visit.pk,
        visibility="CUSTOMER",
    )
    return visit


def report_issue(*, prop: Property, data: dict, actor) -> "MaintenanceIssue":
    from apps.maintenance.models import MaintenanceIssue

    issue = MaintenanceIssue.objects.create(
        property=prop,
        visit_id=data.get("visit"),
        title=data["title"][:180],
        description=data.get("description", ""),
        severity=data.get("severity") or MaintenanceIssue.Severity.MEDIUM,
        estimate_xaf=data.get("estimate_xaf"),
        photo_id=data.get("photo"),
        reported_by=actor,
    )
    record_activity(
        verb="ISSUE_REPORTED",
        message=f"Problème signalé sur {prop.name} : {issue.title}",
        actor=actor,
        property=prop,
        entity_type="MaintenanceIssue",
        entity_id=issue.pk,
        visibility="CUSTOMER",
        is_important=issue.is_urgent,
    )
    if issue.is_urgent:
        notify(
            recipient=prop.owner,
            notification_type=NotificationType.MAINTENANCE,
            title=f"Problème important — {prop.name}",
            body=f"{issue.title}. Gravité : {issue.get_severity_display()}. Un devis vous sera transmis.",
            action_url=f"/espace/proprietes/{prop.pk}",
            action_label="Voir le détail",
            entity_type="MaintenanceIssue",
            entity_id=issue.pk,
            payload={"reference": prop.reference},
            dedupe_key=f"issue:{issue.pk}:urgent",
            also_sms=True,
        )
    return issue
