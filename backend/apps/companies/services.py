"""Services des entreprises BTP : profil, vérification KEMTA, indicateurs.

Une entreprise n'est jamais « vérifiée » par elle-même : KEMTA contrôle les
pièces (RCCM, numéro contribuable, références chantier) puis approuve. C'est ce
contrôle humain qui donne sa valeur au badge affiché sur le catalogue public.
"""
from __future__ import annotations

import logging

from django.db import transaction
from django.db.models import Avg, Count, Sum
from django.utils import timezone

from apps.activities.services import record_activity
from apps.companies.models import (
    Company,
    CompanyDocument,
    CompanyMember,
    VerificationStatus,
)
from apps.notifications.services import notify
from common.constants import NotificationType
from common.utils import humanize_amount, slugify

logger = logging.getLogger("kemta.companies")


def profile_completeness(company: Company) -> int:
    """Pourcentage de complétude du dossier : moteur du parcours d'inscription BTP."""
    checks = [check for _, check in _checks()]
    if not checks:
        return 0
    return round(sum(1 for check in checks if check(company)) / len(checks) * 100)


def _checks():
    return (
        ("description", lambda c: len((c.description or "").strip()) > 80),
        ("logo", lambda c: bool(c.logo_id)),
        ("cover", lambda c: bool(c.cover_id)),
        ("specialties", lambda c: c.specialties.exists()),
        ("regions", lambda c: bool(c.intervention_regions)),
        ("experience", lambda c: (c.years_experience or 0) > 0),
        ("projects_count", lambda c: (c.projects_count or 0) > 0),
        ("registration", lambda c: bool((c.registration_number or "").strip())),
        ("documents", lambda c: c.documents.filter(status="APPROVED").exists()),
        ("realizations", lambda c: c.realizations.exclude(status__in=["DRAFT", "ARCHIVED"]).exists()),
    )


_MISSING_LABELS = {
    "description": ("Présenter l'entreprise (80 caractères minimum)", "/entreprise/profil"),
    "logo": ("Ajouter le logo de l'entreprise", "/entreprise/profil"),
    "cover": ("Ajouter une photo de couverture (chantier ou équipe)", "/entreprise/profil"),
    "specialties": ("Sélectionner vos corps d'état (maçonnerie, électricité…)", "/entreprise/profil"),
    "regions": ("Indiquer vos zones d'intervention", "/entreprise/profil"),
    "experience": ("Renseigner vos années d'expérience", "/entreprise/profil"),
    "projects_count": ("Indiquer le nombre de chantiers réalisés", "/entreprise/profil"),
    "registration": ("Saisir le numéro RCCM", "/entreprise/profil"),
    "documents": ("Faire valider une pièce administrative", "/entreprise/dossier"),
    "realizations": ("Soumettre une première réalisation au catalogue", "/entreprise/realisations"),
}


def missing_items(company: Company) -> list[dict]:
    """Ce qu'il reste à faire, en clair, pour obtenir la vérification KEMTA."""
    if company is None:
        return []
    return [
        {"key": key, "label": _MISSING_LABELS[key][0], "url": _MISSING_LABELS[key][1]}
        for key, check in _checks()
        if not check(company)
    ]


@transaction.atomic
def create_company(*, data: dict, owner, specialties=None) -> Company:
    """Crée le profil entreprise et promeut le compte client en rôle COMPANY."""
    if Company.objects.filter(owner=owner).exists():
        raise ValueError(
            "Un profil entreprise est déjà associé à votre compte. "
            "Utilisez la mise à jour du profil pour le compléter."
        )

    company = Company.objects.create(
        owner=owner,
        name=data["name"].strip(),
        slug=_unique_slug(data["name"]),
        legal_name=data.get("legal_name", ""),
        registration_number=data.get("registration_number", ""),
        tax_number=data.get("tax_number", ""),
        phone=data.get("phone") or owner.phone,
        secondary_phone=data.get("secondary_phone", ""),
        email=data.get("email", ""),
        website=data.get("website", ""),
        city=data.get("city", ""),
        region=data.get("region", ""),
        address=data.get("address", ""),
        country=data.get("country") or owner.country,
        description=data.get("description", ""),
        years_experience=data.get("years_experience") or 0,
        employees_count=data.get("employees_count") or 1,
        projects_count=data.get("projects_count") or 0,
        equipment_summary=data.get("equipment_summary", ""),
        intervention_regions=data.get("intervention_regions") or [],
        intervention_radius_km=data.get("intervention_radius_km") or 50,
        logo=data.get("logo"),
        cover=data.get("cover"),
        verification_status=VerificationStatus.PENDING,
        is_published=False,
    )
    if specialties:
        company.specialties.set(specialties)

    CompanyMember.objects.get_or_create(
        company=company,
        user=owner,
        defaults={
            "role": CompanyMember.MemberRole.OWNER,
            "is_active": True,
            "can_publish_catalog": True,
        },
    )

    if owner.role == "CUSTOMER":
        owner.role = "COMPANY"
        owner.save(update_fields=["role", "updated_at"])

    record_activity(
        verb="COMPANY_CREATED",
        message=f"Profil entreprise créé : {company.name}",
        actor=owner,
        company=company,
        entity_type="Company",
        entity_id=company.pk,
        visibility="TEAM",
        is_important=True,
    )
    _notify_team_new_company(company)
    logger.info("company_created", extra={"company_id": company.pk, "city": company.city})
    return company


def _unique_slug(name: str) -> str:
    base = slugify(name, max_length=60)
    candidate = base
    suffix = 2
    while Company.objects.filter(slug=candidate).exists():
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


def _notify_team_new_company(company: Company) -> None:
    from django.contrib.auth import get_user_model

    User = get_user_model()
    for member in User.objects.filter(role__in=["ADMIN", "MANAGER"], is_active=True):
        notify(
            recipient=member,
            notification_type=NotificationType.SYSTEM,
            title=f"Nouveau dossier entreprise : {company.name}",
            body=(
                f"{company.city or 'Ville non renseignée'} · dossier complété à "
                f"{profile_completeness(company)} % · en attente de vérification."
            ),
            action_url=f"/admin/entreprises/{company.pk}",
            action_label="Ouvrir le dossier",
            entity_type="Company",
            entity_id=company.pk,
            payload={"company": company.name},
            dedupe_key=f"company:{company.pk}:created-team",
        )


@transaction.atomic
def verify_company(*, company: Company, actor, decision: str, notes: str = "") -> Company:
    """Approuve ou rejette la vérification d'une entreprise (contrôle par KEMTA)."""
    if decision == "VERIFIED":
        missing = [item["label"] for item in missing_items(company)]
        if missing:
            raise ValueError(
                "Le dossier est incomplet : "
                + " ; ".join(missing[:4])
                + ". Demandez les pièces manquantes avant de vérifier."
            )
        company.verification_status = VerificationStatus.VERIFIED
        company.is_published = True
        company.verified_at = timezone.now()
        company.verified_by = actor
        company.verification_notes = notes
        title = "Votre entreprise est vérifiée"
        message = (
            "Votre badge KEMTA est actif : votre profil et vos réalisations sont désormais "
            "visibles par les clients et la diaspora."
        )
    else:
        if not (notes or "").strip():
            raise ValueError("Un rejet doit être motivé : l'entreprise doit savoir quoi corriger.")
        company.verification_status = VerificationStatus.REJECTED
        company.verification_notes = notes
        company.is_published = False
        title = "Dossier entreprise à compléter"
        message = f"Votre dossier doit être corrigé : {notes}"

    company.save()

    record_activity(
        verb="COMPANY_VERIFIED" if decision == "VERIFIED" else "COMPANY_STATUS_CHANGED",
        message=f"{company.name} — {company.get_verification_status_display()}",
        actor=actor,
        company=company,
        entity_type="Company",
        entity_id=company.pk,
        visibility="CUSTOMER",
        is_important=True,
    )
    notify(
        recipient=company.owner,
        notification_type=NotificationType.COMPANY,
        title=title,
        body=message,
        action_url="/entreprise/profil",
        action_label="Voir mon profil",
        entity_type="Company",
        entity_id=company.pk,
        payload={"decision": decision},
        dedupe_key=f"company:{company.pk}:verify:{decision}:{timezone.now().date()}",
        also_sms=decision == "VERIFIED",
    )
    return company


@transaction.atomic
def review_company_document(*, document: CompanyDocument, actor, decision: str, notes: str = "") -> CompanyDocument:
    """Valide ou refuse une pièce administrative, et prévient l'entreprise."""
    if decision == "REJECTED" and not (notes or "").strip():
        raise ValueError("Indiquez pourquoi la pièce est refusée : l'entreprise doit pouvoir la corriger.")
    document.status = decision
    document.review_notes = notes[:255]
    document.reviewed_at = timezone.now()
    document.save(update_fields=["status", "review_notes", "reviewed_at"])

    label = document.get_kind_display()
    notify(
        recipient=document.company.owner,
        notification_type=NotificationType.COMPANY,
        title=f"{label} {'validée' if decision == 'APPROVED' else 'à corriger' if decision == 'REJECTED' else 'en attente'}",
        body=(
            f"Pièce « {document.title or label} » : "
            + (f"{notes}" if notes else "validation enregistrée par KEMTA.")
        ),
        action_url="/entreprise/dossier",
        action_label="Voir mon dossier",
        entity_type="CompanyDocument",
        entity_id=document.pk,
        dedupe_key=f"document:{document.pk}:review:{decision}",
        also_sms=decision == "REJECTED",
    )
    return document


def company_stats(company: Company) -> dict:
    """Indicateurs de pilotage de l'entreprise : visibilité, ventes, conformité."""
    from apps.applications.models import Application, ApplicationStatus
    from apps.btp_catalog.models import Realization

    realizations = Realization.objects.filter(company=company)
    applications = Application.objects.filter(company=company)
    reviews = company.reviews.filter(is_published=True).aggregate(
        average=Avg("rating"), count=Count("id")
    )
    views = realizations.aggregate(total=Sum("views_count"))["total"] or 0
    return {
        "realizations": {
            "total": realizations.count(),
            "published": realizations.filter(status="PUBLISHED").count(),
            "pending": realizations.filter(status="PENDING").count(),
            "views": views,
        },
        "applications": {
            "total": applications.count(),
            "pending": applications.filter(
                status__in=[ApplicationStatus.SUBMITTED, ApplicationStatus.REVIEWING]
            ).count(),
            "shortlisted": applications.filter(
                status__in=[ApplicationStatus.SHORTLISTED, ApplicationStatus.INTERVIEW]
            ).count(),
            "awarded": applications.filter(status=ApplicationStatus.AWARDED).count(),
        },
        "documents": {
            "total": company.documents.count(),
            "approved": company.documents.filter(status="APPROVED").count(),
            "pending": company.documents.filter(status="PENDING").count(),
            "rejected": company.documents.filter(status="REJECTED").count(),
        },
        "reviews": {
            "count": reviews["count"] or 0,
            "average": round(float(reviews["average"] or 0), 2),
        },
        "profile_completeness": profile_completeness(company),
        "missing_items": missing_items(company),
        "members": company.members.filter(is_active=True).count(),
        "completed_projects": company.completed_projects_count,
        "rating_label": f"{float(company.rating_average or 0):.1f}/5",
        "public_url": company.public_url,
    }


def company_overview_payload(company: Company) -> dict:
    """Bloc d'en-tête de l'espace entreprise (identité + confiance)."""
    return {
        "id": company.pk,
        "name": company.name,
        "slug": company.slug,
        "city": company.city,
        "is_verified": company.is_verified,
        "verification_status": company.verification_status,
        "verification_status_label": company.get_verification_status_display(),
        "rating_average": float(company.rating_average or 0),
        "rating_count": company.rating_count,
        "logo_url": company.logo_url,
        "cover_url": company.cover_url,
        "public_url": company.public_url,
        "profile_completeness": profile_completeness(company),
        "portfolio_value_label": humanize_amount(0),
    }
