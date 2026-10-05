"""Services des candidatures : dépôt, instruction, notification des entreprises."""
from __future__ import annotations

import logging

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.activities.services import record_activity
from apps.applications.models import Application, ApplicationDocument, ApplicationStatus
from apps.opportunities.models import Opportunity
from apps.notifications.services import notify
from common.constants import NotificationType

logger = logging.getLogger("kemta.applications")


@transaction.atomic
def submit_application(*, opportunity, company, submitted_by, data: dict) -> Application:
    """Dépose une candidature après contrôle d'éligibilité et de capacité du plan."""
    if not opportunity.is_open:
        raise ValueError(
            "Les candidatures pour ce marché sont closes. "
            "Consultez les autres opportunités ouvertes sur KEMTA."
        )
    if opportunity.requires_verified_company and not company.is_verified:
        raise ValueError(
            "Ce marché est réservé aux entreprises vérifiées. "
            "Complétez votre dossier pour obtenir la vérification KEMTA."
        )
    if opportunity.minimum_experience_years and company.years_experience < opportunity.minimum_experience_years:
        raise ValueError(
            f"Ce marché demande au moins {opportunity.minimum_experience_years} ans d'expérience."
        )
    if Application.objects.filter(opportunity=opportunity, company=company).exists():
        raise ValueError("Votre entreprise a déjà candidaté à ce marché. Suivez votre dossier dans vos candidatures.")

    from apps.subscriptions.services import check_application_capacity

    allowed, message = check_application_capacity(company)
    if not allowed:
        raise PermissionError(message)

    application = Application.objects.create(
        opportunity=opportunity,
        company=company,
        submitted_by=submitted_by,
        presentation=data["presentation"],
        similar_experience=data.get("similar_experience", ""),
        methodology=data.get("methodology", ""),
        estimated_budget_xaf=data.get("estimated_budget_xaf"),
        proposed_duration_days=data.get("proposed_duration_days"),
        team_size=data.get("team_size"),
        team_composition=data.get("team_composition", ""),
        message=data.get("message", ""),
        accepts_site_visit=data.get("accepts_site_visit", True),
        contact_override=data.get("contact_override", ""),
    )
    realization_ids = data.get("realization_ids") or []
    if realization_ids:
        valid_ids = list(
            company.realizations.filter(id__in=realization_ids, status="PUBLISHED").values_list("id", flat=True)
        )
        application.relevant_realizations.set(valid_ids)

    document_ids = data.get("document_ids") or []
    kinds = data.get("document_kinds") or {}
    for asset_id in document_ids:
        ApplicationDocument.objects.create(
            application=application,
            kind=kinds.get(str(asset_id), ApplicationDocument.DocumentKind.OTHER),
            asset_id=asset_id,
        )

    Opportunity.objects.filter(pk=opportunity.pk).update(applications_count=F("applications_count") + 1)
    _count_subscription_usage(company)

    record_activity(
        verb="APPLICATION_SUBMITTED",
        message=f"{company.name} a candidaté : {opportunity.title}",
        actor=submitted_by,
        company=company,
        entity_type="Application",
        entity_id=application.pk,
        url=f"/admin/candidatures/{application.pk}",
        visibility="TEAM",
        is_important=True,
        payload={"reference": application.reference, "opportunity": opportunity.reference},
    )
    _notify_team(application)
    _notify_company(application)
    logger.info(
        "application_submitted",
        extra={"reference": application.reference, "opportunity": opportunity.reference},
    )
    return application


def _count_subscription_usage(company) -> None:
    subscription = company.subscriptions.filter(status__in=["TRIALING", "ACTIVE", "PAST_DUE"]).first()
    if subscription is not None:
        from apps.subscriptions.models import Subscription

        Subscription.objects.filter(pk=subscription.pk).update(
            applications_used=F("applications_used") + 1
        )


def _notify_team(application: Application) -> None:
    from django.contrib.auth import get_user_model

    User = get_user_model()
    for member in User.objects.filter(role__in=["ADMIN", "MANAGER"], is_active=True):
        notify(
            recipient=member,
            notification_type=NotificationType.APPLICATION,
            title=f"Nouvelle candidature {application.reference}",
            body=(
                f"{application.company.name} ({application.company.city}) candidate à "
                f"« {application.opportunity.title} ». Notez et présélectionnez les meilleurs dossiers."
            ),
            action_url=f"/admin/candidatures/{application.pk}",
            action_label="Instruire la candidature",
            entity_type="Application",
            entity_id=application.pk,
            payload={"reference": application.reference},
            dedupe_key=f"application:{application.pk}:team:{member.pk}",
        )


def _notify_company(application: Application) -> None:
    notify(
        recipient=application.submitted_by,
        notification_type=NotificationType.APPLICATION,
        title="Votre candidature a été envoyée",
        body=(
            f"Référence {application.reference} pour « {application.opportunity.title} ». "
            "L'équipe KEMTA examine votre dossier et revient vers vous sous 5 jours ouvrés."
        ),
        action_url="/entreprise/candidatures",
        action_label="Suivre mes candidatures",
        entity_type="Application",
        entity_id=application.pk,
        payload={"reference": application.reference},
        dedupe_key=f"application:{application.pk}:ack",
        also_sms=True,
    )


@transaction.atomic
def review_application(*, application: Application, reviewer, data: dict) -> Application:
    """Instruit une candidature (score, notes internes, décision)."""
    previous = application.status
    application.status = data["status"]
    if data.get("score") is not None:
        application.score = data["score"]
    if data.get("internal_notes") is not None:
        application.internal_notes = data["internal_notes"]
    if data.get("client_feedback") is not None:
        application.client_feedback = data["client_feedback"]
    if data.get("rejection_reason"):
        application.rejection_reason = data["rejection_reason"][:255]
    application.reviewed_by = reviewer
    application.reviewed_at = timezone.now()
    if application.status in {ApplicationStatus.AWARDED, ApplicationStatus.REJECTED, ApplicationStatus.WITHDRAWN}:
        application.decided_at = timezone.now()
    application.save()

    record_activity(
        verb="APPLICATION_STATUS_CHANGED",
        message=f"Candidature {application.reference} : {previous} → {application.status}",
        actor=reviewer,
        company=application.company,
        entity_type="Application",
        entity_id=application.pk,
        visibility="TEAM",
    )

    if previous != application.status:
        notify(
            recipient=application.submitted_by,
            notification_type=NotificationType.APPLICATION,
            title=_status_title(application),
            body=_status_body(application),
            action_url="/entreprise/candidatures",
            action_label="Voir ma candidature",
            entity_type="Application",
            entity_id=application.pk,
            payload={"reference": application.reference},
            dedupe_key=f"application:{application.pk}:status:{application.status}",
            also_sms=application.status in {
                ApplicationStatus.SHORTLISTED, ApplicationStatus.INTERVIEW, ApplicationStatus.AWARDED,
            },
        )
    return application


def _status_title(application: Application) -> str:
    return {
        ApplicationStatus.REVIEWING: "Votre candidature est en cours d'examen",
        ApplicationStatus.SHORTLISTED: "Bonne nouvelle : votre candidature est présélectionnée",
        ApplicationStatus.INTERVIEW: "Entretien ou visite de site à programmer",
        ApplicationStatus.AWARDED: "Félicitations : votre candidature est retenue",
        ApplicationStatus.REJECTED: "Votre candidature n'a pas été retenue cette fois",
        ApplicationStatus.WITHDRAWN: "Candidature retirée",
    }.get(application.status, "Votre candidature a été mise à jour")


def _status_body(application: Application) -> str:
    if application.status == ApplicationStatus.REJECTED:
        return (
            application.rejection_reason
            or "Le client a retenu un autre dossier. D'autres opportunités correspondent à votre profil."
        )
    if application.status == ApplicationStatus.AWARDED:
        return (
            f"Marché « {application.opportunity.title} » attribué à {application.company.name}. "
            "KEMTA prend contact pour l'organisation du démarrage."
        )
    if application.status == ApplicationStatus.INTERVIEW:
        return "KEMTA vous contacte pour organiser l'entretien ou la visite du site."
    if application.status == ApplicationStatus.SHORTLISTED:
        return "Votre dossier fait partie de la présélection transmise au client."
    return "Notre équipe poursuit l'analyse de votre dossier."


def withdraw_application(*, application: Application, actor) -> Application:
    if application.is_decided:
        raise ValueError("Cette candidature est déjà close : elle ne peut plus être retirée.")
    application.status = ApplicationStatus.WITHDRAWN
    application.save(update_fields=["status", "updated_at"])
    record_activity(
        verb="APPLICATION_STATUS_CHANGED",
        message=f"Candidature {application.reference} retirée par l'entreprise",
        actor=actor,
        company=application.company,
        entity_type="Application",
        entity_id=application.pk,
        visibility="TEAM",
    )
    return application
