"""Services métier des demandes de service.

Le formulaire est dynamique : chaque service a ses propres champs. Plutôt que de
créer une table par formulaire, on valide les réponses par un schéma (voir
``schemas.py``) puis on alimente les colonnes clés, indexées et filtrables.
"""
from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone

from apps.activities.services import record_activity
from apps.notifications.services import notify
from apps.service_requests.models import (
    RequestStatus,
    ServiceKind,
    ServiceRequest,
    ServiceRequestEvent,
)
from common.constants import NotificationType
from common.utils import normalize_phone

logger = logging.getLogger("kemta.service_requests")


@transaction.atomic
def create_service_request(*, data: dict, attachments: list | None = None, user=None, request=None) -> ServiceRequest:
    """Enregistre une demande (visiteur ou client) et prévient l'équipe KEMTA."""
    payload = data.pop("payload", {}) or {}
    phone = normalize_phone(data.get("phone") or "")
    kind = data.get("kind") or ServiceKind.OTHER

    service_request = ServiceRequest.objects.create(
        kind=kind,
        customer=user if (user and user.is_authenticated) else None,
        phone=phone,
        first_name=(data.get("first_name") or "").strip()[:80],
        last_name=(data.get("last_name") or "").strip()[:80],
        email=(data.get("email") or "").strip()[:254],
        country=(data.get("country") or "CM")[:2].upper(),
        city=(data.get("city") or "").strip()[:120],
        city_of_residence=(data.get("city_of_residence") or "").strip()[:120],
        project_type=(data.get("project_type") or "")[:80],
        location_id=data.get("location_id"),
        location_text=(data.get("location_text") or "")[:200],
        budget_min_xaf=data.get("budget_min_xaf"),
        budget_max_xaf=data.get("budget_max_xaf"),
        spent_xaf=data.get("spent_xaf"),
        desired_start_date=data.get("desired_start_date"),
        description=data.get("description") or "",
        current_progress=(data.get("current_progress") or "")[:120],
        current_company=(data.get("current_company") or "")[:180],
        site_manager=(data.get("site_manager") or "")[:180],
        known_issues=data.get("known_issues") or "",
        objective=data.get("objective") or "",
        maintenance_services=data.get("maintenance_services") or [],
        maintenance_frequency=(data.get("maintenance_frequency") or "")[:20],
        property_type=(data.get("property_type") or "")[:40],
        property_occupied=(data.get("property_occupied") or "")[:20],
        last_visit_date=data.get("last_visit_date"),
        service_id=data.get("service_id"),
        payload=payload,
        source=(data.get("source") or "site")[:40],
        utm=data.get("utm") or {},
        assigned_to=None,
    )

    if attachments:
        for item in attachments:
            item.request = service_request
            item.save()

    ServiceRequestEvent.objects.create(
        request=service_request,
        from_status="",
        to_status=RequestStatus.NEW,
        comment="Demande reçue via le site KEMTA.",
        is_customer_visible=True,
    )

    record_activity(
        verb="REQUEST_RECEIVED",
        message=f"Nouvelle demande {service_request.reference} — {service_request.kind_label}",
        actor=user if (user and user.is_authenticated) else None,
        entity_type="ServiceRequest",
        entity_id=service_request.pk,
        url=f"/admin/demandes/{service_request.pk}",
        visibility="TEAM",
        is_important=True,
        payload={"kind": service_request.kind, "location": service_request.display_location},
    )

    # Alerte interne : les chargés de suivi doivent voir la demande rapidement.
    notify_service_request_received(service_request)

    logger.info(
        "service_request_created",
        extra={"reference": service_request.reference, "kind": service_request.kind},
    )
    return service_request


def notify_service_request_received(service_request: ServiceRequest) -> None:
    """Prévient l'équipe KEMTA (notification interne + confirmation client)."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    team = User.objects.filter(role__in=["ADMIN", "MANAGER"], is_active=True).only("id", "phone", "first_name", "email")
    for member in team:
        notify(
            recipient=member,
            notification_type=NotificationType.SERVICE_REQUEST,
            title=f"Nouvelle demande {service_request.reference}",
            body=(
                f"{service_request.full_name} ({service_request.phone}) — "
                f"{service_request.kind_label} à {service_request.display_location or 'localisation à préciser'}."
            ),
            action_url=f"/admin/demandes/{service_request.pk}",
            action_label="Ouvrir la demande",
            entity_type="ServiceRequest",
            entity_id=service_request.pk,
            payload={"reference": service_request.reference},
            dedupe_key=f"request:{service_request.pk}:team:{member.pk}",
        )

    if service_request.customer_id:
        notify(
            recipient=service_request.customer,
            notification_type=NotificationType.SERVICE_REQUEST,
            title="Votre demande a bien été reçue",
            body=(
                f"Référence {service_request.reference}. Notre équipe étudie votre besoin "
                "et vous contacte sous 48 heures ouvrées."
            ),
            action_url=f"/espace/demandes/{service_request.pk}",
            action_label="Suivre ma demande",
            entity_type="ServiceRequest",
            entity_id=service_request.pk,
            dedupe_key=f"request:{service_request.pk}:ack",
        )
    elif service_request.email:
        from apps.notifications.services import send_transactional_email

        send_transactional_email(
            to=service_request.email,
            subject=f"KEMTA — demande {service_request.reference} reçue",
            body=(
                f"Bonjour {service_request.first_name},\n\n"
                f"Nous avons bien reçu votre demande (référence {service_request.reference}).\n"
                "Un chargé de suivi KEMTA vous contacte sous 48 heures ouvrées.\n\n"
                "L'équipe KEMTA"
            ),
            dedupe_key=f"request-email:{service_request.pk}",
        )


@transaction.atomic
def change_status(
    *, service_request: ServiceRequest, new_status: str, actor, comment: str = "",
    customer_visible: bool = True,
) -> ServiceRequest:
    """Change le statut d'une demande, journalise et notifie le client."""
    previous = service_request.status
    if previous == new_status:
        return service_request

    service_request.status = new_status
    if new_status == RequestStatus.CONTACTED and not service_request.first_contact_at:
        service_request.first_contact_at = timezone.now()
    service_request.save(update_fields=["status", "first_contact_at", "updated_at"])

    ServiceRequestEvent.objects.create(
        request=service_request,
        actor=actor,
        from_status=previous,
        to_status=new_status,
        comment=comment,
        is_customer_visible=customer_visible,
    )

    record_activity(
        verb="REQUEST_STATUS_CHANGED",
        message=f"{service_request.reference} : {previous} → {new_status}",
        actor=actor,
        entity_type="ServiceRequest",
        entity_id=service_request.pk,
        url=f"/admin/demandes/{service_request.pk}",
        visibility="TEAM",
    )

    if service_request.customer_id and customer_visible:
        notify(
            recipient=service_request.customer,
            notification_type=NotificationType.SERVICE_REQUEST,
            title=f"Votre demande {service_request.reference} avance",
            body=comment or service_request.next_step_label,
            action_url=f"/espace/demandes/{service_request.pk}",
            entity_type="ServiceRequest",
            entity_id=service_request.pk,
            dedupe_key=f"request:{service_request.pk}:status:{new_status}",
        )
    return service_request


def service_catalog_payload() -> list[dict]:
    """Catalogue des services (mis en cache) utilisé par la landing et les formulaires."""
    from django.core.cache import cache

    from apps.service_requests.models import ServiceCatalog
    from common.cache import TTL, make_key
    from common.serializers import AssetSerializer

    key = make_key("service_catalog", "v1")
    cached = cache.get(key)
    if cached is not None:
        return cached

    services = list(
        ServiceCatalog.objects.filter(is_active=True).select_related("hero_image").order_by("order", "name")
    )
    payload = [
        {
            "code": service.code,
            "name": service.name,
            "tagline": service.tagline,
            "description": service.description,
            "icon": service.icon,
            "deliverables": service.deliverables or [],
            "base_price_xaf": float(service.base_price_xaf) if service.base_price_xaf else None,
            "duration_days": service.duration_days,
            "requires_site_visit": service.requires_site_visit,
            "hero_image": AssetSerializer(service.hero_image).data if service.hero_image_id else None,
        }
        for service in services
    ]
    cache.set(key, payload, TTL["service_catalog"])
    return payload
