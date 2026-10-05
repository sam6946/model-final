"""Dashboard agrégé de l'espace client.

Exigence produit : à l'ouverture de l'espace, le frontend ne doit faire **qu'un
seul appel** au lieu de 7 (profil, permissions, notifications, projets,
propriétés, statistiques, activité). Tout est assemblé ici en un minimum de
requêtes SQL grâce à ``select_related`` / ``prefetch_related`` et à des
agrégations groupées.
"""
from __future__ import annotations

from django.db.models import Count, Q, Sum
from django.utils import timezone

from apps.activities.models import ActivityLog
from apps.evidences.models import Evidence, EvidenceStatus
from apps.maintenance.models import MaintenanceContract, MaintenanceVisit
from apps.notifications.models import Notification
from apps.projects.models import HealthStatus, Project, ProjectStatus
from apps.properties.models import Property
from apps.service_requests.models import RequestStatus, ServiceRequest
from common.cache import TTL, make_key
from common.permissions import get_user_permissions
from common.utils import humanize_amount


def build_client_dashboard(user) -> dict:
    """Charge utile complète de l'espace client (une seule réponse)."""
    now = timezone.now()
    today = timezone.localdate()

    project_ids = list(
        Project.objects.filter(Q(customer=user) | Q(members__user=user))
        .values_list("id", flat=True)
        .distinct()
    )

    # --- Projets : agrégations groupées, puis liste mise en forme -------------
    project_stats = Project.objects.filter(id__in=project_ids).aggregate(
        total=Count("id"),
        active=Count(
            "id",
            filter=Q(
                status__in=[
                    ProjectStatus.DRAFT, ProjectStatus.PLANNING, ProjectStatus.IN_PROGRESS,
                    ProjectStatus.HANDOVER, ProjectStatus.ON_HOLD,
                ]
            ),
        ),
        completed=Count("id", filter=Q(status=ProjectStatus.COMPLETED)),
        at_risk=Count("id", filter=Q(health=HealthStatus.AT_RISK)),
        watch=Count("id", filter=Q(health=HealthStatus.WATCH)),
        budget_total=Sum("budget_total_xaf"),
        budget_spent=Sum("budget_spent_xaf"),
    )

    project_cards = list(
        Project.objects.filter(id__in=project_ids)
        .select_related("cover", "manager", "company", "location")
        .prefetch_related("phases")
        .order_by("-updated_at")[:6]
    )

    # --- Propriétés ----------------------------------------------------------
    properties = Property.objects.filter(Q(owner=user) | Q(manager=user)).distinct()
    property_stats = properties.aggregate(
        total=Count("id"),
        vacant=Count("id", filter=Q(occupancy_status="VACANT")),
        rented=Count("id", filter=Q(occupancy_status="RENTED")),
        estimated_value=Sum("estimated_value_xaf"),
    )
    property_cards = list(
        properties.select_related("cover", "location").order_by("-updated_at")[:4]
    )

    # --- Demandes de service -------------------------------------------------
    requests_stats = ServiceRequest.objects.filter(Q(customer=user) | Q(phone=user.phone)).aggregate(
        total=Count("id"),
        open=Count(
            "id",
            filter=~Q(
                status__in=[RequestStatus.CONVERTED, RequestStatus.CLOSED, RequestStatus.REJECTED]
            ),
        ),
        converted=Count("id", filter=Q(status=RequestStatus.CONVERTED)),
    )
    recent_requests = list(
        ServiceRequest.objects.filter(Q(customer=user) | Q(phone=user.phone))
        .order_by("-created_at")
        .only(
            "id", "reference", "kind", "status", "location_text", "city", "created_at",
            "budget_min_xaf", "budget_max_xaf", "first_name", "last_name",
        )[:4]
    )

    # --- Preuves à découvrir -------------------------------------------------
    pending_evidences = Evidence.objects.filter(
        project_id__in=project_ids, status=EvidenceStatus.VALIDATED
    ).count()
    latest_evidences = list(
        Evidence.objects.filter(project_id__in=project_ids, status=EvidenceStatus.VALIDATED)
        .select_related("asset", "project", "captured_by")
        .order_by("-captured_at", "-created_at")[:8]
    )

    # --- Entretien -----------------------------------------------------------
    contracts = MaintenanceContract.objects.filter(
        Q(customer=user) | Q(property__owner=user)
    )
    maintenance_stats = contracts.aggregate(
        total=Count("id"),
        active=Count("id", filter=Q(status=MaintenanceContract.Status.ACTIVE)),
    )
    next_visits = list(
        MaintenanceVisit.objects.filter(
            Q(property__owner=user) | Q(property__manager=user),
            status__in=[MaintenanceVisit.Status.SCHEDULED, MaintenanceVisit.Status.CONFIRMED],
            scheduled_for__gte=now,
        )
        .select_related("property", "technician")
        .order_by("scheduled_for")[:4]
    )

    # --- Notifications et activité ------------------------------------------
    notifications = list(
        Notification.objects.filter(recipient=user)
        .order_by("-created_at")
        .only("id", "notification_type", "level", "title", "body", "action_url", "action_label", "read_at", "created_at")[:8]
    )
    unread_count = Notification.objects.filter(recipient=user, read_at__isnull=True).count()

    recent_activity = list(
        ActivityLog.objects.filter(
            Q(project_id__in=project_ids) | Q(actor=user), visibility__in=["CUSTOMER", "PUBLIC"]
        )
        .select_related("actor", "project")
        .order_by("-created_at")[:12]
    )

    # --- Factures / paiements ------------------------------------------------
    from apps.payments.models import Invoice, InvoiceStatus

    invoice_stats = Invoice.objects.filter(customer=user).aggregate(
        unpaid=Count(
            "id",
            filter=Q(status__in=[InvoiceStatus.SENT, InvoiceStatus.PARTIALLY_PAID, InvoiceStatus.OVERDUE]),
        ),
        outstanding=Sum("total_xaf", filter=Q(status__in=[InvoiceStatus.SENT, InvoiceStatus.PARTIALLY_PAID]))
        - Sum("amount_paid_xaf", filter=Q(status__in=[InvoiceStatus.SENT, InvoiceStatus.PARTIALLY_PAID])),
    )

    return {
        "user": _user_payload(user),
        "permissions": sorted(get_user_permissions(user)),
        "spaces": _spaces(user),
        "statistics": {
            "projects": {
                "total": project_stats["total"] or 0,
                "active": project_stats["active"] or 0,
                "completed": project_stats["completed"] or 0,
                "at_risk": (project_stats["at_risk"] or 0) + (project_stats["watch"] or 0),
                "budget_total_xaf": float(project_stats["budget_total"] or 0),
                "budget_total_label": humanize_amount(project_stats["budget_total"] or 0),
                "budget_spent_xaf": float(project_stats["budget_spent"] or 0),
                "budget_spent_label": humanize_amount(project_stats["budget_spent"] or 0),
                "budget_used_percent": round(
                    float(project_stats["budget_spent"] or 0)
                    / float(project_stats["budget_total"] or 1)
                    * 100,
                    1,
                ),
            },
            "properties": {
                "total": property_stats["total"] or 0,
                "vacant": property_stats["vacant"] or 0,
                "rented": property_stats["rented"] or 0,
                "portfolio_value_xaf": float(property_stats["estimated_value"] or 0),
                "portfolio_value_label": humanize_amount(property_stats["estimated_value"] or 0),
            },
            "requests": {
                "total": requests_stats["total"] or 0,
                "open": requests_stats["open"] or 0,
                "converted": requests_stats["converted"] or 0,
            },
            "maintenance": {
                "contracts_total": maintenance_stats["total"] or 0,
                "contracts_active": maintenance_stats["active"] or 0,
                "next_visits": len(next_visits),
            },
            "evidences": {
                "published": pending_evidences,
            },
            "billing": {
                "unpaid_invoices": invoice_stats["unpaid"] or 0,
                "outstanding_label": humanize_amount(invoice_stats["outstanding"] or 0),
            },
            "notifications": {"unread": unread_count},
        },
        "projects": [_project_card(project) for project in project_cards],
        "properties": [_property_card(prop) for prop in property_cards],
        "requests": [_request_card(item) for item in recent_requests],
        "organizations": _organizations(user),
        "next_visits": [_visit_card(visit) for visit in next_visits],
        "latest_evidences": [_evidence_card(evidence) for evidence in latest_evidences],
        "notifications": [_notification_card(item) for item in notifications],
        "recent_activity": [_activity_card(item) for item in recent_activity],
        "next_actions": _next_actions(
            project_ids=project_ids,
            expired_visits=next_visits,
            unread_count=unread_count,
            requests_open=requests_stats["open"] or 0,
            today=today,
        ),
        "generated_at": now,
    }


def _user_payload(user) -> dict:
    return {
        "id": user.pk,
        "full_name": user.full_name,
        "first_name": user.first_name,
        "initials": user.initials,
        "phone": user.phone,
        "phone_verified": user.phone_verified,
        "email": user.email or "",
        "role": user.role,
        "role_label": user.get_role_display(),
        "city": user.city,
        "country": user.country,
        "avatar_url": user.avatar.thumbnail_url if user.avatar_id else "",
        "is_diaspora": _is_diaspora(user),
    }


def _is_diaspora(user) -> bool:
    profile = getattr(user, "customer_profile", None)
    if profile is None:
        return user.country not in {"CM", ""}
    return profile.is_diaspora


def _spaces(user) -> list[dict]:
    spaces = [{"key": "customer", "label": "Espace client", "url": "/espace", "available": True}]
    company = getattr(user, "primary_company", None)
    spaces.append(
        {
            "key": "company",
            "label": "Espace entreprise BTP",
            "url": "/entreprise",
            "available": bool(company),
            "company_name": company.name if company else "",
        }
    )
    if user.is_kemta_team:
        spaces.append({"key": "admin", "label": "Back-office KEMTA", "url": "/admin", "available": True})
    return spaces


def _organizations(user) -> list[dict]:
    organizations = []
    company = getattr(user, "primary_company", None)
    if company is not None:
        organizations.append(
            {
                "id": company.pk,
                "kind": "COMPANY",
                "name": company.name,
                "slug": company.slug,
                "role": company.members.filter(user=user).values_list("role", flat=True).first(),
                "verification_status": company.verification_status,
                "logo_url": company.logo_url,
            }
        )
    return organizations


def _project_card(project: Project) -> dict:
    return {
        "id": project.pk,
        "reference": project.reference,
        "name": project.name,
        "slug": project.slug,
        "status": project.status,
        "status_label": project.get_status_display(),
        "health": project.health,
        "health_label": project.get_health_display(),
        "kind": project.kind,
        "kind_label": project.get_kind_display(),
        "location": project.display_location,
        "cover_url": project.cover_url,
        "progress_percent": float(project.physical_progress),
        "budget_used_percent": project.budget_used_percent,
        "budget_label": humanize_amount(project.budget_total_xaf) if project.budget_total_xaf else "",
        "manager_name": project.manager.full_name if project.manager_id else "",
        "company_name": project.company.name if project.company_id else "",
        "is_late": project.is_late,
        "planned_end": project.planned_end,
        "updated_at": project.updated_at,
    }


def _property_card(prop: Property) -> dict:
    return {
        "id": prop.pk,
        "reference": prop.reference,
        "name": prop.name,
        "type_label": prop.get_property_type_display(),
        "occupancy_label": prop.get_occupancy_status_display(),
        "location": prop.display_location,
        "cover_url": prop.cover_url,
        "needs_attention": prop.needs_attention,
        "last_visited_at": prop.last_visited_at,
        "next_visit_at": prop.next_visit_at,
    }


def _request_card(item: ServiceRequest) -> dict:
    return {
        "id": item.pk,
        "reference": item.reference,
        "kind": item.kind,
        "kind_label": item.get_kind_display(),
        "status": item.status,
        "status_label": item.get_status_display(),
        "next_step": item.next_step_label,
        "location": item.location_text or item.city,
        "created_at": item.created_at,
    }


def _visit_card(visit: MaintenanceVisit) -> dict:
    return {
        "id": visit.pk,
        "reference": visit.reference,
        "property_name": visit.property.name,
        "property_id": visit.property_id,
        "scheduled_for": visit.scheduled_for,
        "status": visit.status,
        "status_label": visit.get_status_display(),
        "technician_name": visit.technician.full_name if visit.technician_id else "",
    }


def _evidence_card(evidence: Evidence) -> dict:
    return {
        "id": evidence.pk,
        "project_id": evidence.project_id,
        "project_name": evidence.project.name if evidence.project_id else "",
        "kind": evidence.kind,
        "title": evidence.title or evidence.get_kind_display(),
        "caption": evidence.caption,
        "thumbnail_url": evidence.thumbnail_url,
        "preview_url": evidence.preview_url,
        "captured_at": evidence.effective_capture_date,
        "freshness_label": evidence.freshness_label,
        "phase_name": evidence.phase.name if evidence.phase_id else "",
    }


def _notification_card(item: Notification) -> dict:
    return {
        "id": item.pk,
        "type": item.notification_type,
        "level": item.level,
        "title": item.title,
        "body": item.body,
        "action_url": item.action_url,
        "action_label": item.action_label,
        "is_read": item.read_at is not None,
        "created_at": item.created_at,
    }


def _activity_card(item: ActivityLog) -> dict:
    return {
        "id": item.pk,
        "verb": item.verb,
        "verb_label": item.get_verb_display(),
        "message": item.message,
        "actor_name": item.actor.full_name if item.actor_id else "Équipe KEMTA",
        "actor_initials": item.actor.initials if item.actor_id else "KE",
        "project_reference": item.project.reference if item.project_id else "",
        "is_important": item.is_important,
        "created_at": item.created_at,
    }


def _next_actions(*, project_ids, expired_visits, unread_count, requests_open, today) -> list[dict]:
    """Actions recommandées : transforme les données en prochaine étape concrète."""
    actions: list[dict] = []
    if unread_count:
        actions.append(
            {
                "key": "notifications",
                "label": f"{unread_count} notification(s) non lue(s)",
                "url": "/espace/notifications",
                "priority": 2,
                "kind": "info",
            }
        )
    if requests_open:
        actions.append(
            {
                "key": "requests",
                "label": f"{requests_open} demande(s) en cours d'étude par KEMTA",
                "url": "/espace/demandes",
                "priority": 3,
                "kind": "info",
            }
        )
    late_projects = Project.objects.filter(
        id__in=project_ids, planned_end__lt=today
    ).exclude(status__in=[ProjectStatus.COMPLETED, ProjectStatus.CANCELLED]).count()
    if late_projects:
        actions.append(
            {
                "key": "late_projects",
                "label": f"{late_projects} chantier(s) en retard sur le planning prévu",
                "url": "/espace/projets?filter=late",
                "priority": 1,
                "kind": "warning",
            }
        )
    if expired_visits:
        actions.append(
            {
                "key": "visits",
                "label": f"{len(expired_visits)} visite(s) d'entretien programmée(s)",
                "url": "/espace/proprietes",
                "priority": 3,
                "kind": "info",
            }
        )
    actions.sort(key=lambda item: item["priority"])
    return actions[:4]


def build_company_dashboard(user) -> dict:
    """Espace entreprise BTP : activité commerciale et visibilité."""
    from apps.applications.models import Application, ApplicationStatus
    from apps.btp_catalog.models import Realization
    from apps.companies.services import company_stats
    from apps.opportunities.models import Opportunity, OpportunityStatus
    from apps.subscriptions.services import current_subscription, effective_limits

    company = getattr(user, "primary_company", None)
    if company is None:
        return {
            "company": None,
            "onboarding_required": True,
            "next_steps": [
                "Créer votre profil entreprise (nom, ville, activités)",
                "Déposer vos pièces administratives pour la vérification",
                "Publier vos premières réalisations",
            ],
        }

    stats = company_stats(company)
    subscription = current_subscription(company)
    applications = (
        Application.objects.filter(company=company)
        .select_related("opportunity")
        .order_by("-created_at")[:6]
    )
    opportunities = (
        Opportunity.objects.filter(
            status=OpportunityStatus.OPEN,
            application_deadline__gte=timezone.localdate(),
        )
        .exclude(applications__company=company)
        .select_related("location")
        .order_by("-published_at")[:5]
    )
    invoices = company.invoices.order_by("-issued_at")[:5]
    realizations = (
        Realization.objects.filter(company=company).select_related("cover").order_by("-updated_at")[:6]
    )

    return {
        "user": _user_payload(user),
        "permissions": sorted(get_user_permissions(user)),
        "company": {
            "id": company.pk,
            "name": company.name,
            "slug": company.slug,
            "verification_status": company.verification_status,
            "verification_status_label": company.get_verification_status_display(),
            "is_verified": company.is_verified,
            "is_published": company.is_published,
            "is_featured": company.is_featured,
            "logo_url": company.logo_url,
            "cover_url": company.cover_url,
            "city": company.city,
            "rating_average": float(company.rating_average or 0),
            "rating_count": company.rating_count,
            "profile_completeness": stats["profile_completeness"],
            "public_url": company.public_url,
        },
        "statistics": {
            **stats,
            "opportunities_available": opportunities.count(),
        },
        "subscription": {
            "plan_code": subscription.plan.code if subscription else "FREE",
            "plan_name": subscription.plan.name if subscription else "Découverte",
            "status": subscription.status if subscription else "NONE",
            "days_remaining": subscription.days_remaining if subscription else None,
            "renews_soon": subscription.renews_soon if subscription else False,
            "limits": effective_limits(company),
        },
        "applications": [
            {
                "id": item.pk,
                "reference": item.reference,
                "status": item.status,
                "status_label": item.get_status_display(),
                "opportunity_title": item.opportunity.title,
                "opportunity_slug": item.opportunity.slug,
                "location": item.opportunity.display_location,
                "created_at": item.created_at,
            }
            for item in applications
        ],
        "opportunities": [
            {
                "id": item.pk,
                "reference": item.reference,
                "title": item.title,
                "slug": item.slug,
                "location": item.display_location,
                "budget_label": item.budget_label,
                "deadline": item.application_deadline,
                "days_left": item.days_left,
                "property_type": item.property_type,
            }
            for item in opportunities
        ],
        "realizations": [
            {
                "id": item.pk,
                "title": item.title,
                "slug": item.slug,
                "status": item.status,
                "status_label": item.get_status_display(),
                "cover_url": item.cover_url,
                "views_count": item.views_count,
                "year": item.year,
            }
            for item in realizations
        ],
        "invoices": [
            {
                "id": invoice.pk,
                "number": invoice.number,
                "total_label": humanize_amount(invoice.total_xaf),
                "status": invoice.status,
                "display_status": invoice.display_status,
                "due_at": invoice.due_at,
            }
            for invoice in invoices
        ],
        "notifications": [
            _notification_card(item)
            for item in Notification.objects.filter(recipient=user).order_by("-created_at")[:6]
        ],
        "recent_activity": [
            _activity_card(item)
            for item in ActivityLog.objects.filter(company=company)
            .select_related("actor", "project")
            .order_by("-created_at")[:10]
        ],
        "next_actions": _company_next_actions(company, stats, opportunities.count()),
    }


def _company_next_actions(company, stats, opportunities_count: int) -> list[dict]:
    actions: list[dict] = []
    if company.verification_status == "PENDING":
        actions.append(
            {
                "key": "verification",
                "label": "Complétez vos documents pour obtenir la vérification KEMTA",
                "url": "/entreprise/dossier",
                "kind": "warning",
                "priority": 1,
            }
        )
    if company.verification_status == "REJECTED":
        actions.append(
            {
                "key": "verification_rejected",
                "label": "Votre dossier doit être complété (voir le retour KEMTA)",
                "url": "/entreprise/dossier",
                "kind": "error",
                "priority": 1,
            }
        )
    if stats["realizations"]["published"] < 3:
        actions.append(
            {
                "key": "catalog",
                "label": "Publiez au moins 3 réalisations pour inspirer confiance",
                "url": "/entreprise/realisations",
                "kind": "info",
                "priority": 2,
            }
        )
    if opportunities_count:
        actions.append(
            {
                "key": "opportunities",
                "label": f"{opportunities_count} marché(s) ouvert(s) correspondant à votre profil",
                "url": "/entreprise/opportunites",
                "kind": "success",
                "priority": 2,
            }
        )
    if stats["profile_completeness"] < 100:
        actions.append(
            {
                "key": "profile",
                "label": f"Profil complété à {stats['profile_completeness']} %",
                "url": "/entreprise/profil",
                "kind": "info",
                "priority": 3,
            }
        )
    actions.sort(key=lambda item: item["priority"])
    return actions[:4]


def build_admin_dashboard(user) -> dict:
    """Back-office KEMTA : vision consolidée de l'activité de la plateforme."""
    from apps.applications.models import Application, ApplicationStatus
    from apps.companies.models import Company, VerificationStatus
    from apps.opportunities.models import Opportunity, OpportunityStatus
    from apps.payments.models import Invoice, InvoiceStatus, Payment, PaymentStatus
    from apps.subscriptions.models import Subscription

    today = timezone.localdate()
    last_30 = timezone.now() - timezone.timedelta(days=30)

    project_stats = Project.objects.aggregate(
        total=Count("id"),
        active=Count(
            "id",
            filter=Q(status__in=[ProjectStatus.PLANNING, ProjectStatus.IN_PROGRESS, ProjectStatus.HANDOVER]),
        ),
        completed=Count("id", filter=Q(status=ProjectStatus.COMPLETED)),
        at_risk=Count("id", filter=Q(health=HealthStatus.AT_RISK)),
        new_last_30=Count("id", filter=Q(created_at__gte=last_30)),
        budget_total=Sum("budget_total_xaf"),
        budget_spent=Sum("budget_spent_xaf"),
    )
    request_stats = ServiceRequest.objects.aggregate(
        total=Count("id"),
        new=Count("id", filter=Q(status=RequestStatus.NEW)),
        open=Count(
            "id",
            filter=~Q(status__in=[RequestStatus.CONVERTED, RequestStatus.CLOSED, RequestStatus.REJECTED]),
        ),
        qualified=Count("id", filter=Q(status=RequestStatus.QUALIFIED)),
        new_last_30=Count("id", filter=Q(created_at__gte=last_30)),
    )
    company_stats = Company.objects.aggregate(
        total=Count("id"),
        pending=Count("id", filter=Q(verification_status=VerificationStatus.PENDING)),
        verified=Count("id", filter=Q(verification_status=VerificationStatus.VERIFIED)),
        published=Count("id", filter=Q(is_published=True)),
    )
    application_stats = Application.objects.aggregate(
        total=Count("id"),
        pending=Count("id", filter=Q(status__in=[ApplicationStatus.SUBMITTED, ApplicationStatus.REVIEWING])),
        shortlisted=Count("id", filter=Q(status=ApplicationStatus.SHORTLISTED)),
        awarded=Count("id", filter=Q(status=ApplicationStatus.AWARDED)),
    )
    opportunity_stats = Opportunity.objects.aggregate(
        total=Count("id"),
        open=Count("id", filter=Q(status=OpportunityStatus.OPEN, application_deadline__gte=today)),
        closing_soon=Count(
            "id",
            filter=Q(status=OpportunityStatus.OPEN, application_deadline__lte=today + timezone.timedelta(days=7)),
        ),
    )
    payment_stats = Payment.objects.aggregate(
        total=Count("id"),
        succeeded=Count("id", filter=Q(status=PaymentStatus.SUCCEEDED)),
        pending=Count("id", filter=Q(status__in=[PaymentStatus.PENDING, PaymentStatus.PROCESSING])),
        failed=Count("id", filter=Q(status=PaymentStatus.FAILED)),
        collected_last_30=Sum("amount_xaf", filter=Q(status=PaymentStatus.SUCCEEDED, paid_at__gte=last_30)),
        collected_total=Sum("amount_xaf", filter=Q(status=PaymentStatus.SUCCEEDED)),
    )
    invoice_stats = Invoice.objects.aggregate(
        unpaid=Count(
            "id", filter=Q(status__in=[InvoiceStatus.SENT, InvoiceStatus.PARTIALLY_PAID, InvoiceStatus.OVERDUE])
        ),
        overdue=Count("id", filter=Q(due_at__lt=today) & ~Q(status__in=[InvoiceStatus.PAID, InvoiceStatus.VOID])),
        outstanding=Sum("total_xaf", filter=Q(status__in=[InvoiceStatus.SENT, InvoiceStatus.PARTIALLY_PAID])),
    )
    subscription_stats = Subscription.objects.aggregate(
        total=Count("id"),
        active=Count("id", filter=Q(status=Subscription.Status.ACTIVE)),
        trialing=Count("id", filter=Q(status=Subscription.Status.TRIALING)),
        past_due=Count("id", filter=Q(status=Subscription.Status.PAST_DUE)),
    )
    evidence_stats = Evidence.objects.aggregate(
        pending=Count("id", filter=Q(status=EvidenceStatus.PENDING)),
        validated=Count("id", filter=Q(status=EvidenceStatus.VALIDATED)),
        total=Count("id"),
    )

    projects_at_risk = (
        Project.objects.filter(health=HealthStatus.AT_RISK)
        .exclude(status__in=[ProjectStatus.COMPLETED, ProjectStatus.CANCELLED])
        .select_related("customer", "manager")
        .order_by("-updated_at")[:5]
    )
    pending_companies = (
        Company.objects.filter(verification_status=VerificationStatus.PENDING)
        .select_related("owner")
        .order_by("created_at")[:5]
    )

    return {
        "user": _user_payload(user),
        "permissions": sorted(get_user_permissions(user)),
        "statistics": {
            "projects": {**{k: v or 0 for k, v in project_stats.items()}},
            "requests": {**{k: v or 0 for k, v in request_stats.items()}},
            "companies": {**{k: v or 0 for k, v in company_stats.items()}},
            "applications": {**{k: v or 0 for k, v in application_stats.items()}},
            "opportunities": {**{k: v or 0 for k, v in opportunity_stats.items()}},
            "payments": {
                **{k: v or 0 for k, v in payment_stats.items()},
                "collected_last_30_label": humanize_amount(payment_stats["collected_last_30"] or 0),
                "collected_total_label": humanize_amount(payment_stats["collected_total"] or 0),
            },
            "invoices": {
                **{k: v or 0 for k, v in invoice_stats.items()},
                "outstanding_label": humanize_amount(invoice_stats["outstanding"] or 0),
            },
            "subscriptions": {**{k: v or 0 for k, v in subscription_stats.items()}},
            "evidences": {**{k: v or 0 for k, v in evidence_stats.items()}},
        },
        "projects_at_risk": [
            {
                "id": project.pk,
                "reference": project.reference,
                "name": project.name,
                "customer_name": project.customer.full_name if project.customer_id else "",
                "manager_name": project.manager.full_name if project.manager_id else "",
                "progress_percent": float(project.physical_progress),
                "budget_used_percent": project.budget_used_percent,
                "planned_end": project.planned_end,
                "is_late": project.is_late,
            }
            for project in projects_at_risk
        ],
        "pending_companies": [
            {
                "id": company.pk,
                "name": company.name,
                "city": company.city,
                "owner_name": company.owner.full_name if company.owner_id else "",
                "owner_phone": company.owner.phone if company.owner_id else "",
                "created_at": company.created_at,
            }
            for company in pending_companies
        ],
        "recent_activity": [
            _activity_card(item)
            for item in ActivityLog.objects.select_related("actor", "project").order_by("-created_at")[:15]
        ],
        "notifications": [
            _notification_card(item)
            for item in Notification.objects.filter(recipient=user).order_by("-created_at")[:8]
        ],
        "next_actions": _admin_next_actions(request_stats, company_stats, evidence_stats, invoice_stats),
    }


def _admin_next_actions(request_stats, company_stats, evidence_stats, invoice_stats) -> list[dict]:
    actions: list[dict] = []
    if request_stats["new"]:
        actions.append(
            {
                "key": "new_requests",
                "label": f"{request_stats['new']} nouvelle(s) demande(s) à qualifier",
                "url": "/admin/demandes?status=NEW",
                "kind": "warning",
                "priority": 1,
            }
        )
    if company_stats["pending"]:
        actions.append(
            {
                "key": "pending_companies",
                "label": f"{company_stats['pending']} dossier(s) d'entreprise à vérifier",
                "url": "/admin/entreprises?status=PENDING",
                "kind": "warning",
                "priority": 1,
            }
        )
    if evidence_stats["pending"]:
        actions.append(
            {
                "key": "pending_evidences",
                "label": f"{evidence_stats['pending']} preuve(s) terrain à valider",
                "url": "/admin/preuves",
                "kind": "info",
                "priority": 2,
            }
        )
    if invoice_stats["overdue"]:
        actions.append(
            {
                "key": "overdue_invoices",
                "label": f"{invoice_stats['overdue']} facture(s) en retard de paiement",
                "url": "/admin/factures?status=overdue",
                "kind": "error",
                "priority": 2,
            }
        )
    actions.sort(key=lambda item: item["priority"])
    return actions[:5]


def invalidate_dashboard(*users) -> None:
    """Invalide le cache du tableau de bord des utilisateurs concernés.

    Sans cela, un client verrait un compteur figé jusqu'à deux minutes après
    l'ajout d'un chantier, d'une preuve ou d'une notification.
    """
    from django.core.cache import cache

    today = timezone.localdate()
    for user in users:
        if user is None or not getattr(user, "pk", None):
            continue
        cache.delete(make_key("dashboard_client", user.pk, today))


def cached_dashboard(*, user, namespace: str, builder) -> tuple[dict, bool]:
    """Met en cache les tableaux de bord 2 minutes (données semi-dynamiques).

    Le cache est invalidé naturellement par TTL court : un back-office peut
    tolérer 2 minutes de décalage sur des compteurs globaux, pas sur ses
    propres actions (les écritures invalident leur propre namespace).
    """
    from django.core.cache import cache

    key = make_key(namespace, user.pk, timezone.localdate())
    cached = cache.get(key)
    if cached is not None:
        return cached, True
    payload = builder(user)
    cache.set(key, payload, TTL["dashboard_stats"])
    return payload, False
