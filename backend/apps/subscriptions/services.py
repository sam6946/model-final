"""Services d'abonnement BTP : plans, souscription, limites d'usage.

Les prix et les limites viennent exclusivement de la base : le frontend ne
contient aucun tarif en dur (exigence produit explicite).
"""
from __future__ import annotations

import logging
from datetime import timedelta

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from apps.activities.services import record_activity
from apps.companies.models import Company, VerificationStatus
from apps.notifications.services import notify
from apps.subscriptions.models import INTERVAL_MONTHS, BillingInterval, Plan, Subscription
from common.cache import TTL, make_key
from common.constants import NotificationType
from common.utils import humanize_amount

logger = logging.getLogger("kemta.subscriptions")

DEFAULT_PLAN_LIMITS = {
    "FREE": {"realizations": 3, "photos_per_realization": 6, "applications_per_month": 2, "featured": False,
             "sms_notifications": False, "verified_badge": True, "priority_support": False},
    "PRO": {"realizations": 20, "photos_per_realization": 20, "applications_per_month": 15, "featured": True,
            "sms_notifications": True, "verified_badge": True, "priority_support": False},
    "PREMIUM": {"realizations": None, "photos_per_realization": 40, "applications_per_month": None,
                "featured": True, "sms_notifications": True, "verified_badge": True, "priority_support": True},
}


def plans_payload() -> list[dict]:
    """Plans publics (mis en cache Redis, TTL 15 min)."""
    key = make_key("plans", "public", "v1")
    cached = cache.get(key)
    if cached is not None:
        return cached
    plans = Plan.objects.filter(is_active=True, is_public=True).order_by("sort_order", "price_xaf")
    payload = [
        {
            "id": plan.pk,
            "code": plan.code,
            "name": plan.name,
            "tagline": plan.tagline,
            "description": plan.description,
            "price_xaf": float(plan.price_xaf or 0),
            "price_label": plan.price_label,
            "currency": plan.currency,
            "interval": plan.interval,
            "trial_days": plan.trial_days,
            "features": plan.features or [],
            "limits": plan.limits or DEFAULT_PLAN_LIMITS.get(plan.code.upper(), {}),
            "is_recommended": plan.is_recommended,
            "is_free": plan.is_free,
            "monthly_equivalent_xaf": float(plan.monthly_equivalent_xaf),
        }
        for plan in plans
    ]
    cache.set(key, payload, TTL["plans"])
    return payload


def current_subscription(company: Company) -> Subscription | None:
    return (
        company.subscriptions.filter(status__in=["TRIALING", "ACTIVE", "PAST_DUE"])
        .select_related("plan")
        .order_by("-created_at")
        .first()
    )


def effective_limits(company: Company) -> dict:
    """Limites applicables : abonnement en cours, sinon plan Découverte."""
    subscription = current_subscription(company)
    if subscription is not None:
        return {**DEFAULT_PLAN_LIMITS.get("FREE", {}), **(subscription.plan.limits or {})}
    plan = Plan.objects.filter(code="FREE", is_active=True).first()
    if plan is not None:
        return {**DEFAULT_PLAN_LIMITS["FREE"], **(plan.limits or {})}
    return DEFAULT_PLAN_LIMITS["FREE"]


def check_realization_capacity(company: Company) -> tuple[bool, str]:
    """L'entreprise peut-elle publier une réalisation supplémentaire ?"""
    from apps.btp_catalog.models import Realization

    limits = effective_limits(company)
    maximum = limits.get("realizations")
    if maximum is None:
        return True, ""
    used = Realization.objects.filter(company=company).exclude(status="ARCHIVED").count()
    if used < int(maximum):
        return True, ""
    plan_name = _current_plan_name(company)
    return False, (
        f"Votre offre {plan_name} permet {int(maximum)} réalisations publiées, et vous en avez déjà {used}. "
        "Passez à une offre supérieure pour en publier davantage."
    )


def check_application_capacity(company: Company) -> tuple[bool, str]:
    """L'entreprise peut-elle candidater encore ce mois-ci ?"""
    limits = effective_limits(company)
    maximum = limits.get("applications_per_month")
    if maximum is None:
        return True, ""
    subscription = current_subscription(company)
    if subscription is None:
        # Sans abonnement : quota du plan Découverte sur le mois calendaire.
        from apps.applications.models import Application

        month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        used = Application.objects.filter(company=company, created_at__gte=month_start).count()
    else:
        used = subscription.applications_used
    if used < int(maximum):
        return True, ""
    return False, (
        f"Votre offre {_current_plan_name(company)} autorise {int(maximum)} candidatures par mois "
        f"et vous en avez déjà déposé {used}. Passez à une offre supérieure pour candidater davantage."
    )


def _current_plan_name(company: Company) -> str:
    subscription = current_subscription(company)
    if subscription is not None:
        return subscription.plan.name
    plan = Plan.objects.filter(code="FREE", is_active=True).first()
    return plan.name if plan else "Découverte"


@transaction.atomic
def subscribe_company(*, company: Company, plan: Plan, actor, provider: str = "MANUAL") -> Subscription:
    """Souscrit ou change de plan ; crée la facture correspondante."""
    if not plan.is_active:
        raise ValueError("Cette offre n'est plus disponible.")

    existing = current_subscription(company)
    if existing is not None and existing.plan_id == plan.pk:
        raise ValueError(f"Votre entreprise est déjà abonnée à l'offre {plan.name}.")

    if existing is not None:
        existing.status = Subscription.Status.CANCELLED
        existing.cancelled_at = timezone.now()
        existing.ended_at = timezone.now()
        existing.cancel_at_period_end = False
        existing.save(update_fields=["status", "cancelled_at", "ended_at", "cancel_at_period_end", "updated_at"])

    months = INTERVAL_MONTHS.get(plan.interval, 1)
    now = timezone.now()
    subscription = Subscription.objects.create(
        company=company,
        plan=plan,
        status=Subscription.Status.TRIALING if plan.trial_days else Subscription.Status.ACTIVE,
        started_at=now,
        current_period_start=now,
        current_period_end=now + timedelta(days=plan.trial_days or months * 30),
        trial_ends_at=(now + timedelta(days=plan.trial_days)) if plan.trial_days else None,
        price_xaf_snapshot=plan.price_xaf,
        provider=provider,
        seats=max(1, company.employees_count and 1 or 1),
    )

    invoice = None
    if not plan.is_free:
        from apps.payments.services import create_subscription_invoice

        invoice = create_subscription_invoice(subscription=subscription, actor=actor)

    record_activity(
        verb="SUBSCRIPTION_CHANGED",
        message=f"{company.name} — offre {plan.name} activée",
        actor=actor,
        company=company,
        entity_type="Subscription",
        entity_id=subscription.pk,
        visibility="TEAM",
        is_important=True,
    )
    notify(
        recipient=company.owner,
        notification_type=NotificationType.SUBSCRIPTION,
        title=f"Offre {plan.name} activée",
        body=(
            f"Votre entreprise bénéficie désormais de l'offre {plan.name}. "
            + (f"Facture {invoice.number} à régler avant le {invoice.due_at}." if invoice else
               "Aucun paiement n'est requis pour cette offre.")
        ),
        action_url="/entreprise/abonnement",
        action_label="Gérer mon abonnement",
        entity_type="Subscription",
        entity_id=subscription.pk,
        payload={"amount_label": plan.price_label},
        dedupe_key=f"subscription:{subscription.pk}:activated",
        also_sms=bool(plan.is_recommended),
    )
    logger.info("subscription_created", extra={"company_id": company.pk, "plan": plan.code})
    return subscription


@transaction.atomic
def activate_on_payment(*, payment) -> None:
    """Active/reprolonge l'abonnement lorsqu'un paiement est encaissé."""
    subscription = payment.subscription
    if subscription is None:
        return
    if subscription.status == Subscription.Status.TRIALING:
        subscription.status = Subscription.Status.ACTIVE
        subscription.trial_ends_at = None
        months = INTERVAL_MONTHS.get(subscription.plan.interval, 1)
        subscription.current_period_end = timezone.now() + timedelta(days=months * 30)
        subscription.save(update_fields=["status", "trial_ends_at", "current_period_end", "updated_at"])
    else:
        subscription.extend_period()
    notify(
        recipient=subscription.company.owner,
        notification_type=NotificationType.SUBSCRIPTION,
        title="Paiement reçu — abonnement prolongé",
        body=(
            f"Votre offre {subscription.plan.name} est active jusqu'au "
            f"{timezone.localtime(subscription.current_period_end).strftime('%d/%m/%Y')}."
        ),
        action_url="/entreprise/abonnement",
        action_label="Voir mon abonnement",
        entity_type="Subscription",
        entity_id=subscription.pk,
        payload={"amount_label": humanize_amount(payment.amount_xaf)},
        dedupe_key=f"subscription:{subscription.pk}:paid:{payment.pk}",
    )
