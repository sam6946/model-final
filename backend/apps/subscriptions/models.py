"""Abonnements BTP : plans configurables, jamais de prix en dur dans le front.

Les tarifs et les limites d'usage vivent en base : KEMTA peut lancer une offre,
ajuster un prix ou une limite depuis l'administration sans redéployer le
frontend, qui récupère les plans via ``GET /api/v1/plans/`` (mis en cache).
"""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from common.constants import Currency


class PlanCode(models.TextChoices):
    FREE = "FREE", "Découverte"
    PRO = "PRO", "Pro"
    PREMIUM = "PREMIUM", "Premium"


class BillingInterval(models.TextChoices):
    MONTHLY = "MONTHLY", "Mensuel"
    QUARTERLY = "QUARTERLY", "Trimestriel"
    YEARLY = "YEARLY", "Annuel"


INTERVAL_MONTHS = {
    BillingInterval.MONTHLY: 1,
    BillingInterval.QUARTERLY: 3,
    BillingInterval.YEARLY: 12,
}


class Plan(models.Model):
    """Offre d'abonnement pour les entreprises BTP (administrable)."""

    code = models.SlugField("code", max_length=40, unique=True)
    name = models.CharField("nom commercial", max_length=120)
    tagline = models.CharField("accroche", max_length=200, blank=True)
    description = models.TextField("description", blank=True)

    price_xaf = models.DecimalField(
        "prix (FCFA)", max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)]
    )
    currency = models.CharField("devise", max_length=3, choices=Currency.choices, default=Currency.XAF)
    interval = models.CharField(
        "périodicité", max_length=12, choices=BillingInterval.choices, default=BillingInterval.MONTHLY
    )
    trial_days = models.PositiveSmallIntegerField("période d'essai (jours)", default=0)

    features = models.JSONField(
        "avantages affichés", default=list, blank=True,
        help_text="Liste de chaînes affichées sur la page tarifs.",
    )
    limits = models.JSONField(
        "limites d'usage", default=dict, blank=True,
        help_text=(
            "Ex. {'realizations': 5, 'photos_per_realization': 10, "
            "'applications_per_month': 3, 'featured': false}"
        ),
    )
    is_public = models.BooleanField("visible publiquement", default=True)
    is_active = models.BooleanField("actif", default=True)
    is_recommended = models.BooleanField("mis en avant", default=False)
    sort_order = models.PositiveIntegerField("ordre", default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "plan d'abonnement"
        verbose_name_plural = "plans d'abonnement"
        ordering = ("sort_order", "price_xaf")
        indexes = [models.Index(fields=("is_active", "is_public", "sort_order"))]

    def __str__(self) -> str:
        return f"{self.name} — {self.price_label}"

    @property
    def price_label(self) -> str:
        if not self.price_xaf:
            return "Gratuit"
        from common.utils import humanize_amount

        suffix = {
            BillingInterval.MONTHLY: "/ mois",
            BillingInterval.QUARTERLY: "/ trimestre",
            BillingInterval.YEARLY: "/ an",
        }.get(self.interval, "")
        return f"{humanize_amount(self.price_xaf, self.currency)} {suffix}".strip()

    @property
    def monthly_equivalent_xaf(self) -> Decimal:
        months = INTERVAL_MONTHS.get(self.interval, 1)
        return (self.price_xaf or Decimal("0")) / months

    def limit_for(self, key: str, default=None):
        return (self.limits or {}).get(key, default)

    @property
    def is_free(self) -> bool:
        return not self.price_xaf


class Subscription(models.Model):
    """Abonnement d'une entreprise BTP à un plan."""

    class Status(models.TextChoices):
        TRIALING = "TRIALING", "Période d'essai"
        ACTIVE = "ACTIVE", "Actif"
        PAST_DUE = "PAST_DUE", "Impayé"
        CANCELLED = "CANCELLED", "Résilié"
        EXPIRED = "EXPIRED", "Expiré"

    company = models.ForeignKey(
        "companies.Company", verbose_name="entreprise", on_delete=models.CASCADE,
        related_name="subscriptions",
    )
    plan = models.ForeignKey(
        Plan, verbose_name="plan", on_delete=models.PROTECT, related_name="subscriptions"
    )
    status = models.CharField("statut", max_length=12, choices=Status.choices, default=Status.ACTIVE, db_index=True)

    started_at = models.DateTimeField("début", default=timezone.now)
    current_period_start = models.DateTimeField("période en cours depuis", default=timezone.now)
    current_period_end = models.DateTimeField("période en cours jusqu'au", db_index=True)
    trial_ends_at = models.DateTimeField("fin d'essai", null=True, blank=True)
    cancelled_at = models.DateTimeField("résilié le", null=True, blank=True)
    cancel_at_period_end = models.BooleanField("résiliation à échéance", default=False)
    ended_at = models.DateTimeField("terminé le", null=True, blank=True)

    price_xaf_snapshot = models.DecimalField(
        "prix contractuel (FCFA)", max_digits=12, decimal_places=2, default=0,
        help_text="Prix figé à la souscription : un changement de tarif ne touche pas les contrats en cours.",
    )
    seats = models.PositiveSmallIntegerField("utilisateurs inclus", default=1)
    provider = models.CharField("moyen de paiement", max_length=16, default="MANUAL")
    provider_reference = models.CharField("référence fournisseur", max_length=120, blank=True)
    auto_renew = models.BooleanField("renouvellement automatique", default=True)

    # Compteurs d'usage de la période (remis à zéro au renouvellement)
    applications_used = models.PositiveIntegerField("candidatures ce mois", default=0)

    notes = models.CharField("notes", max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "abonnement"
        verbose_name_plural = "abonnements"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("status", "current_period_end")),
            models.Index(fields=("company", "status")),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=("company",),
                condition=models.Q(status__in=["TRIALING", "ACTIVE", "PAST_DUE"]),
                name="uniq_active_subscription_per_company",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.company.name} — {self.plan.name} ({self.get_status_display()})"

    # -- État -------------------------------------------------------------
    @property
    def is_active(self) -> bool:
        return self.status in {self.Status.TRIALING, self.Status.ACTIVE}

    @property
    def is_trial(self) -> bool:
        return self.status == self.Status.TRIALING and bool(self.trial_ends_at)

    @property
    def days_remaining(self) -> int:
        return max(0, (self.current_period_end - timezone.now()).days)

    @property
    def renews_soon(self) -> bool:
        return self.is_active and self.days_remaining <= 5

    def limit_for(self, key: str, default=None):
        return self.plan.limit_for(key, default)

    def has_capacity(self, key: str, current_usage: int) -> bool:
        limit = self.limit_for(key)
        if limit is None:
            return True  # pas de limite définie = illimité
        try:
            return current_usage < int(limit)
        except (TypeError, ValueError):
            return True

    # -- Cycle de vie -----------------------------------------------------
    def extend_period(self, *, months: int | None = None) -> None:
        """Prolonge la période courante (renouvellement ou encaissement)."""
        from dateutil.relativedelta import relativedelta  # type: ignore

        months = months or INTERVAL_MONTHS.get(self.plan.interval, 1)
        self.current_period_start = self.current_period_end
        self.current_period_end = self.current_period_end + relativedelta(months=months)
        self.applications_used = 0
        self.status = self.Status.ACTIVE
        self.save(update_fields=[
            "current_period_start", "current_period_end", "applications_used", "status", "updated_at",
        ])

    def start_trial(self) -> None:
        if not self.plan.trial_days:
            return
        self.status = self.Status.TRIALING
        self.trial_ends_at = timezone.now() + timedelta(days=self.plan.trial_days)
        self.current_period_end = self.trial_ends_at
        self.save(update_fields=["status", "trial_ends_at", "current_period_end", "updated_at"])
