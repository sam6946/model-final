"""Tâches Celery de l'entretien : rappels de visite, planification continue."""
from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger("kemta.tasks.maintenance")


@shared_task(name="apps.maintenance.tasks.send_visit_reminders")
def send_visit_reminders(days_ahead: int = 2) -> int:
    """Rappelle au client et au technicien les visites à venir (J-2)."""
    from apps.maintenance.models import MaintenanceVisit
    from apps.notifications.services import notify
    from common.constants import NotificationType

    horizon = timezone.now() + timedelta(days=days_ahead)
    visits = (
        MaintenanceVisit.objects.filter(
            status__in=[MaintenanceVisit.Status.SCHEDULED, MaintenanceVisit.Status.CONFIRMED],
            scheduled_for__lte=horizon,
            scheduled_for__gte=timezone.now(),
            client_notified_at__isnull=True,
        )
        .select_related("property", "property__owner", "technician")
        .order_by("scheduled_for")[:200]
    )
    count = 0
    for visit in visits:
        moment = timezone.localtime(visit.scheduled_for).strftime("%d/%m/%Y à %H:%M")
        body = f"Visite {visit.reference} prévue le {moment} pour {visit.property.name}."
        if visit.technician_id:
            notify(
                recipient=visit.technician,
                notification_type=NotificationType.MAINTENANCE,
                title="Visite d'entretien à réaliser",
                body=body,
                action_url=f"/terrain/visites/{visit.pk}",
                action_label="Ouvrir la visite",
                entity_type="MaintenanceVisit",
                entity_id=visit.pk,
                dedupe_key=f"visit:{visit.pk}:tech-reminder",
                also_sms=True,
            )
        notify(
            recipient=visit.property.owner,
            notification_type=NotificationType.MAINTENANCE,
            title="Votre visite d'entretien approche",
            body=body,
            action_url=f"/espace/proprietes/{visit.property_id}",
            action_label="Voir le planning",
            entity_type="MaintenanceVisit",
            entity_id=visit.pk,
            payload={"reference": visit.reference},
            dedupe_key=f"visit:{visit.pk}:client-reminder",
        )
        MaintenanceVisit.objects.filter(pk=visit.pk).update(client_notified_at=timezone.now())
        count += 1
    return count


@shared_task(name="apps.maintenance.tasks.plan_recurring_visits")
def plan_recurring_visits() -> int:
    """Maintient un horizon de visites planifiées pour les contrats actifs."""
    from apps.maintenance.models import MaintenanceContract, MaintenanceVisit

    created_total = 0
    contracts = MaintenanceContract.objects.filter(
        status=MaintenanceContract.Status.ACTIVE, auto_generate_visits=True
    ).select_related("property")
    for contract in contracts:
        upcoming = contract.visits.filter(
            status__in=[MaintenanceVisit.Status.SCHEDULED, MaintenanceVisit.Status.CONFIRMED]
        ).count()
        if upcoming < (contract.visits_included or 1):
            created_total += len(contract.generate_next_visits(count=(contract.visits_included or 1) - upcoming))
    return created_total


@shared_task(name="apps.maintenance.tasks.flag_neglected_properties")
def flag_neglected_properties(days: int = 60) -> int:
    """Alerte sur les biens vacants non contrôlés depuis longtemps (argument commercial)."""
    from apps.notifications.services import notify
    from apps.properties.models import OccupancyStatus, Property
    from common.constants import NotificationType

    threshold = timezone.now() - timedelta(days=days)
    properties = Property.objects.filter(
        is_active=True,
        occupancy_status__in=[OccupancyStatus.VACANT, OccupancyStatus.GUARDED],
    ).filter(models_q(threshold)).select_related("owner", "manager")[:200]

    count = 0
    for prop in properties:
        for recipient in filter(None, [prop.manager_id and prop.manager, prop.owner]):
            notify(
                recipient=recipient,
                notification_type=NotificationType.MAINTENANCE,
                title=f"Bien non contrôlé depuis {days} jours",
                body=(
                    f"{prop.name} ({prop.display_location}) n'a pas fait l'objet d'une visite récente. "
                    "Programmer un contrôle évite les mauvaises surprises (fuite, squat, dégradation)."
                ),
                action_url=f"/espace/proprietes/{prop.pk}",
                action_label="Programmer une visite",
                entity_type="Property",
                entity_id=prop.pk,
                dedupe_key=f"property:{prop.pk}:neglected:{timezone.localdate().isoformat()}",
            )
            count += 1
    return count


def models_q(threshold):
    from django.db.models import Q

    return Q(last_visited_at__lt=threshold) | Q(last_visited_at__isnull=True)
