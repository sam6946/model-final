"""Entretien immobilier : contrats, visites planifiées, interventions.

Le service « entretien » est un revenu récurrent : un contrat définit une
fréquence et une liste de prestations, le système génère les visites à venir,
et chaque visite produit un compte rendu illustré (photos avant/après).
"""
from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from common.models import ReferenceCounter


model_property = property  # le champ « property » du modèle masque le décorateur natif

class MaintenanceServiceType(models.Model):
    """Prestation d'entretien élémentaire (nettoyage, plomberie, jardinage…)."""

    code = models.SlugField("code", max_length=60, unique=True)
    name = models.CharField("libellé", max_length=120)
    description = models.CharField("description", max_length=255, blank=True)
    icon = models.CharField("icône", max_length=40, blank=True)
    base_price_xaf = models.DecimalField(
        "tarif indicatif (FCFA)", max_digits=12, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)],
    )
    unit = models.CharField("unité", max_length=40, default="intervention")
    requires_technician = models.BooleanField("nécessite un technicien", default=False)
    order = models.PositiveIntegerField("ordre", default=0)
    is_active = models.BooleanField("active", default=True)

    class Meta:
        verbose_name = "prestation d'entretien"
        verbose_name_plural = "prestations d'entretien"
        ordering = ("order", "name")
        indexes = [models.Index(fields=("is_active", "order"))]

    def __str__(self) -> str:
        return self.name


class MaintenanceFrequency(models.TextChoices):
    PUNCTUAL = "PUNCTUAL", "Ponctuelle"
    MONTHLY = "MONTHLY", "Mensuelle"
    QUARTERLY = "QUARTERLY", "Trimestrielle"
    SEMIANNUAL = "SEMIANNUAL", "Semestrielle"
    ANNUAL = "ANNUAL", "Annuelle"
    ON_DEMAND = "ON_DEMAND", "Sur demande"


FREQUENCY_DAYS = {
    MaintenanceFrequency.MONTHLY: 30,
    MaintenanceFrequency.QUARTERLY: 90,
    MaintenanceFrequency.SEMIANNUAL: 182,
    MaintenanceFrequency.ANNUAL: 365,
}


class MaintenanceContract(models.Model):
    """Contrat d'entretien d'une propriété (récurrent ou ponctuel)."""

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Brouillon"
        ACTIVE = "ACTIVE", "Actif"
        PAUSED = "PAUSED", "En pause"
        ENDED = "ENDED", "Terminé"
        CANCELLED = "CANCELLED", "Annulé"

    reference = models.CharField("référence", max_length=40, unique=True)
    property = models.ForeignKey(
        "properties.Property", verbose_name="propriété", on_delete=models.CASCADE,
        related_name="maintenance_contracts",
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="client", on_delete=models.PROTECT,
        related_name="maintenance_contracts",
    )
    frequency = models.CharField(
        "fréquence", max_length=12, choices=MaintenanceFrequency.choices,
        default=MaintenanceFrequency.QUARTERLY,
    )
    services = models.ManyToManyField(
        MaintenanceServiceType, verbose_name="prestations", related_name="contracts", blank=True
    )
    status = models.CharField("statut", max_length=12, choices=Status.choices, default=Status.DRAFT, db_index=True)
    start_date = models.DateField("début", default=timezone.localdate)
    end_date = models.DateField("fin", null=True, blank=True)
    price_xaf = models.DecimalField(
        "montant du contrat (FCFA)", max_digits=12, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)],
    )
    billing_cycle_months = models.PositiveSmallIntegerField("facturation (mois)", default=1)
    visits_included = models.PositiveSmallIntegerField("visites incluses", default=1)
    auto_generate_visits = models.BooleanField("planifier automatiquement les visites", default=True)
    assigned_team = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="équipe affectée", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="assigned_maintenance_contracts",
    )
    instructions = models.TextField("consignes particulières", blank=True)
    internal_notes = models.TextField("notes internes", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="créé par", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "contrat d'entretien"
        verbose_name_plural = "contrats d'entretien"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("status", "-created_at")),
            models.Index(fields=("customer", "status")),
            models.Index(fields=("property", "status")),
        ]

    def __str__(self) -> str:
        return f"{self.reference} — {self.property.name}"

    def save(self, *args, **kwargs) -> None:
        if not self.reference:
            self.reference = ReferenceCounter.next_reference("ENT", width=5)
        super().save(*args, **kwargs)

    @model_property
    def is_active(self) -> bool:
        return self.status == self.Status.ACTIVE

    @model_property
    def interval_days(self) -> int:
        return FREQUENCY_DAYS.get(self.frequency, 0)

    @model_property
    def monthly_price_xaf(self) -> float:
        """Coût mensualisé : base de comparaison pour le client."""
        if not self.price_xaf:
            return 0.0
        cycle = max(1, self.billing_cycle_months or 1)
        return float(self.price_xaf) / cycle

    @model_property
    def next_visit(self):
        return (
            self.visits.filter(status__in=[MaintenanceVisit.Status.SCHEDULED, MaintenanceVisit.Status.IN_PROGRESS])
            .order_by("scheduled_for")
            .first()
        )

    def generate_next_visits(self, *, count: int = 3) -> list["MaintenanceVisit"]:
        """Planifie les prochaines visites selon la fréquence contractuelle."""
        if not self.auto_generate_visits or not self.interval_days:
            return []
        anchor = self.next_visit
        cursor = anchor.scheduled_for if anchor else timezone.now() + timedelta(days=1)
        if self.last_generated_visit_at:
            cursor = max(cursor, self.last_generated_visit_at + timedelta(days=self.interval_days))
        created: list[MaintenanceVisit] = []
        for _ in range(count):
            visit = MaintenanceVisit.objects.create(
                contract=self,
                property=self.property,
                scheduled_for=cursor,
                technician=self.assigned_team,
                status=MaintenanceVisit.Status.SCHEDULED,
            )
            cursor = cursor + timedelta(days=self.interval_days)
            created.append(visit)
        MaintenanceContract.objects.filter(pk=self.pk).update(last_generated_visit_at=cursor)
        return created

    last_generated_visit_at = models.DateTimeField("dernière planification", null=True, blank=True)


class MaintenanceVisit(models.Model):
    """Visite d'entretien ou d'inspection sur une propriété."""

    class Status(models.TextChoices):
        SCHEDULED = "SCHEDULED", "Planifiée"
        CONFIRMED = "CONFIRMED", "Confirmée"
        IN_PROGRESS = "IN_PROGRESS", "En cours"
        DONE = "DONE", "Réalisée"
        CANCELLED = "CANCELLED", "Annulée"
        MISSED = "MISSED", "Non réalisée"

    reference = models.CharField("référence", max_length=40, unique=True)
    contract = models.ForeignKey(
        MaintenanceContract, verbose_name="contrat", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="visits",
    )
    property = models.ForeignKey(
        "properties.Property", verbose_name="propriété", on_delete=models.CASCADE, related_name="visits"
    )
    scheduled_for = models.DateTimeField("planifiée le", db_index=True)
    estimated_duration_minutes = models.PositiveSmallIntegerField("durée estimée (min)", default=90)
    completed_at = models.DateTimeField("réalisée le", null=True, blank=True)
    status = models.CharField("statut", max_length=12, choices=Status.choices, default=Status.SCHEDULED, db_index=True)
    technician = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="technicien", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="maintenance_visits",
    )
    services_performed = models.ManyToManyField(
        MaintenanceServiceType, verbose_name="prestations réalisées", related_name="visits", blank=True
    )
    checklist = models.JSONField(
        "points de contrôle", default=list, blank=True,
        help_text="Liste [{label, done, comment}]",
    )
    report = models.TextField("compte rendu", blank=True)
    customer_visible_report = models.TextField("compte rendu client", blank=True)
    recommendations = models.TextField("recommandations", blank=True)
    issues_found = models.PositiveSmallIntegerField("problèmes constatés", default=0)
    condition_score = models.PositiveSmallIntegerField("état constaté (sur 100)", null=True, blank=True)
    cost_xaf = models.DecimalField(
        "coût de l'intervention (FCFA)", max_digits=12, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)],
    )
    access_notes = models.CharField("accès / clés", max_length=255, blank=True)
    photos_count = models.PositiveSmallIntegerField("photos envoyées", default=0)
    client_notified_at = models.DateTimeField("client informé le", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "visite d'entretien"
        verbose_name_plural = "visites d'entretien"
        ordering = ("-scheduled_for",)
        indexes = [
            models.Index(fields=("status", "scheduled_for")),
            models.Index(fields=("property", "-scheduled_for")),
            models.Index(fields=("technician", "status")),
        ]

    def __str__(self) -> str:
        return f"{self.reference} — {self.property.name}"

    def save(self, *args, **kwargs) -> None:
        if not self.reference:
            self.reference = ReferenceCounter.next_reference("VIS", width=5)
        super().save(*args, **kwargs)

    @model_property
    def is_upcoming(self) -> bool:
        return self.status in {self.Status.SCHEDULED, self.Status.CONFIRMED} and self.scheduled_for >= timezone.now()

    @model_property
    def is_overdue(self) -> bool:
        return self.status in {self.Status.SCHEDULED, self.Status.CONFIRMED} and self.scheduled_for < timezone.now()

    @model_property
    def checklist_done_ratio(self) -> float:
        items = self.checklist or []
        if not items:
            return 0.0
        done = sum(1 for item in items if item.get("done"))
        return round(done / len(items) * 100, 1)

    def complete(self, *, report: str = "", score: int | None = None, actor=None) -> None:
        self.status = self.Status.DONE
        self.completed_at = timezone.now()
        self.report = report or self.report
        if score is not None:
            self.condition_score = max(0, min(100, int(score)))
        self.save(update_fields=["status", "completed_at", "report", "condition_score", "updated_at"])
        self.property.register_visit(at=self.completed_at, score=self.condition_score)


class MaintenanceIssue(models.Model):
    """Problème constaté lors d'une visite, avec suivi de traitement."""

    class Severity(models.TextChoices):
        LOW = "LOW", "Mineur"
        MEDIUM = "MEDIUM", "À traiter"
        HIGH = "HIGH", "Important"
        CRITICAL = "CRITICAL", "Urgent / sécurité"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Ouvert"
        QUOTED = "QUOTED", "Devis transmis"
        APPROVED = "APPROVED", "Validé par le client"
        SCHEDULED = "SCHEDULED", "Réparation planifiée"
        FIXED = "FIXED", "Réparé"
        REJECTED = "REJECTED", "Refusé par le client"
        IGNORED = "IGNORED", "Sans suite"

    property = models.ForeignKey(
        "properties.Property", verbose_name="propriété", on_delete=models.CASCADE, related_name="issues"
    )
    visit = models.ForeignKey(
        MaintenanceVisit, verbose_name="visite", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="issues",
    )
    title = models.CharField("problème", max_length=180)
    description = models.TextField("description", blank=True)
    severity = models.CharField("gravité", max_length=8, choices=Severity.choices, default=Severity.MEDIUM)
    status = models.CharField("statut", max_length=10, choices=Status.choices, default=Status.OPEN, db_index=True)
    estimate_xaf = models.DecimalField(
        "coût estimé (FCFA)", max_digits=12, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)],
    )
    photo = models.ForeignKey(
        "common.Asset", verbose_name="photo du problème", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="maintenance_issues",
    )
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="signalé par", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="reported_issues",
    )
    resolved_at = models.DateTimeField("résolu le", null=True, blank=True)
    resolution_notes = models.CharField("notes de résolution", max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "problème constaté"
        verbose_name_plural = "problèmes constatés"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("status", "severity")),
            models.Index(fields=("property", "status")),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.get_severity_display()})"

    @model_property
    def is_urgent(self) -> bool:
        return self.severity in {self.Severity.HIGH, self.Severity.CRITICAL} and self.status not in {
            self.Status.FIXED, self.Status.IGNORED, self.Status.REJECTED,
        }
