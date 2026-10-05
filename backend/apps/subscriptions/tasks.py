"""Tâches Celery des abonnements : facturation récurrente, relances, expirations."""
from __future__ import annotations

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger("kemta.tasks.subscriptions")


@shared_task(name="apps.subscriptions.tasks.run_recurring_billing")
def run_recurring_billing(days_ahead: int = 3) -> dict:
    """Émet les factures des abonnements arrivant à échéance.

    Objectif opérationnel : ne jamais couper un client faute de facture émise
    à temps, sans pour autant encaisser deux fois.
    """
    from apps.payments.services import create_subscription_invoice
    from apps.subscriptions.models import Subscription

    horizon = timezone.now() + timezone.timedelta(days=days_ahead)
    due = Subscription.objects.filter(
        status=Subscription.Status.ACTIVE,
        auto_renew=True,
        current_period_end__lte=horizon,
    ).select_related("company", "plan")[:500]

    invoiced, trials_ended = 0, 0
    for subscription in due:
        if subscription.plan.is_free:
            subscription.extend_period()
            continue
        already = subscription.invoices.filter(
            status__in=["DRAFT", "SENT", "PARTIALLY_PAID"], issued_at__gte=timezone.localdate()
        ).exists()
        if not already:
            create_subscription_invoice(subscription=subscription, actor=None)
            invoiced += 1
    return {"invoiced": invoiced, "trials_ended": trials_ended}


@shared_task(name="apps.subscriptions.tasks.expire_subscriptions")
def expire_subscriptions(grace_days: int = 7) -> int:
    """Fait passer en impayé puis expire les abonnements non réglés."""
    from apps.subscriptions.models import Subscription

    grace_limit = timezone.now() - timezone.timedelta(days=grace_days)
    past_due = Subscription.objects.filter(
        status=Subscription.Status.ACTIVE, current_period_end__lt=grace_limit
    ).update(status=Subscription.Status.PAST_DUE)
    expired = Subscription.objects.filter(
        status=Subscription.Status.PAST_DUE,
        current_period_end__lt=timezone.now() - timezone.timedelta(days=30),
    ).update(status=Subscription.Status.EXPIRED, ended_at=timezone.now())
    return past_due + expired


@shared_task(name="apps.subscriptions.tasks.remind_renewals")
def remind_renewals(days_ahead: int = 5) -> int:
    """Rappelle aux entreprises la prochaine échéance d'abonnement."""
    from apps.notifications.services import notify
    from apps.subscriptions.models import Subscription
    from common.constants import NotificationType

    horizon = timezone.now() + timezone.timedelta(days=days_ahead)
    subscriptions = Subscription.objects.filter(
        status__in=[Subscription.Status.ACTIVE, Subscription.Status.TRIALING],
        current_period_end__lte=horizon,
        current_period_end__gte=timezone.now(),
    ).select_related("company", "plan")[:300]

    count = 0
    for subscription in subscriptions:
        notify(
            recipient=subscription.company.owner,
            notification_type=NotificationType.SUBSCRIPTION,
            title="Votre abonnement arrive à échéance",
            body=(
                f"L'offre {subscription.plan.name} se renouvelle le "
                f"{timezone.localtime(subscription.current_period_end).strftime('%d/%m/%Y')} "
                f"({subscription.plan.price_label})."
            ),
            action_url="/entreprise/abonnement",
            action_label="Gérer mon abonnement",
            entity_type="Subscription",
            entity_id=subscription.pk,
            payload={"amount_label": subscription.plan.price_label},
            dedupe_key=f"subscription:{subscription.pk}:renewal:{subscription.current_period_end.date()}",
        )
        count += 1
    return count
