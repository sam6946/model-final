"""Rapports de chantier : le document que le client attend.

Le rapport quotidien est saisi par le terrain (souvent sur mobile, parfois hors
ligne), puis compilé en rapport périodique destiné au client : avancement,
présence, météo, incidents, décisions à prendre. KEMTA peut générer un PDF
(celui-ci est produit par une tâche Celery afin de ne pas bloquer la requête).
"""
from __future__ import annotations

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from apps.projects.models import Project


class DailyReport(models.Model):
    """Compte rendu journalier du chantier (un seul par projet et par jour)."""

    class Weather(models.TextChoices):
        SUNNY = "SUNNY", "Ensoleillé"
        CLOUDY = "CLOUDY", "Nuageux"
        RAINY = "RAINY", "Pluvieux"
        STORM = "STORM", "Orage"
        HEATWAVE = "HEATWAVE", "Forte chaleur"

    project = models.ForeignKey(
        Project, verbose_name="projet", on_delete=models.CASCADE, related_name="daily_reports"
    )
    report_date = models.DateField("date du rapport", default=timezone.localdate, db_index=True)
    weather = models.CharField("météo", max_length=10, choices=Weather.choices, default=Weather.SUNNY)
    workers_count = models.PositiveSmallIntegerField("effectif présent", default=0)
    supervisors_count = models.PositiveSmallIntegerField("encadrement présent", default=0)
    progress_percent = models.DecimalField(
        "avancement constaté (%)", max_digits=5, decimal_places=2, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    works_done = models.TextField("travaux réalisés", blank=True)
    works_planned = models.TextField("travaux prévus demain", blank=True)
    blockers = models.TextField("difficultés rencontrées", blank=True)
    decisions_needed = models.TextField("décisions attendues du client", blank=True)
    materials_received = models.JSONField("matériaux reçus", default=list, blank=True)
    equipment_used = models.CharField("matériel utilisé", max_length=255, blank=True)
    safety_notes = models.CharField("consignes / sécurité", max_length=255, blank=True)
    hours_worked = models.DecimalField("heures travaillées", max_digits=5, decimal_places=2, default=0)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="rédigé par", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="daily_reports",
    )
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="validé par", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="validated_daily_reports",
    )
    validated_at = models.DateTimeField("validé le", null=True, blank=True)
    is_visible_to_customer = models.BooleanField("visible par le client", default=False)
    client_viewed_at = models.DateTimeField("vu par le client le", null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "rapport journalier"
        verbose_name_plural = "rapports journaliers"
        ordering = ("-report_date",)
        constraints = [
            models.UniqueConstraint(fields=("project", "report_date"), name="uniq_daily_report"),
        ]
        indexes = [
            models.Index(fields=("project", "-report_date")),
            models.Index(fields=("is_visible_to_customer", "-report_date")),
        ]

    def __str__(self) -> str:
        return f"Rapport {self.report_date} — {self.project.reference}"

    @property
    def is_approved(self) -> bool:
        return self.validated_at is not None

    @property
    def total_present(self) -> int:
        return (self.workers_count or 0) + (self.supervisors_count or 0)

    def validate_by(self, user, *, visible_to_customer: bool = True) -> None:
        self.validated_by = user
        self.validated_at = timezone.now()
        self.is_visible_to_customer = visible_to_customer
        self.save(update_fields=["validated_by", "validated_at", "is_visible_to_customer", "updated_at"])


class PeriodicReport(models.Model):
    """Rapport de synthèse (hebdomadaire ou mensuel) transmis au client."""

    class Period(models.TextChoices):
        WEEKLY = "WEEKLY", "Hebdomadaire"
        MONTHLY = "MONTHLY", "Mensuel"
        PHASE = "PHASE", "Fin de phase"
        FINAL = "FINAL", "Réception / rapport final"
        CUSTOM = "CUSTOM", "Sur mesure"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Brouillon"
        GENERATING = "GENERATING", "Génération en cours"
        READY = "READY", "Prêt"
        SENT = "SENT", "Transmis au client"
        FAILED = "FAILED", "Échec de génération"

    project = models.ForeignKey(
        Project, verbose_name="projet", on_delete=models.CASCADE, related_name="periodic_reports"
    )
    period = models.CharField("périodicité", max_length=8, choices=Period.choices, default=Period.WEEKLY)
    title = models.CharField("titre", max_length=200)
    period_start = models.DateField("début de période")
    period_end = models.DateField("fin de période")
    summary = models.TextField("synthèse", blank=True)
    progress_snapshot = models.JSONField("indicateurs", default=dict, blank=True)
    highlights = models.JSONField("points marquants", default=list, blank=True)
    risks = models.JSONField("risques et alertes", default=list, blank=True)
    next_steps = models.JSONField("prochaines étapes", default=list, blank=True)
    financial_summary = models.JSONField("synthèse financière", default=dict, blank=True)

    file = models.ForeignKey(
        "common.Asset", verbose_name="PDF généré", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="periodic_reports",
    )
    status = models.CharField("statut", max_length=12, choices=Status.choices, default=Status.DRAFT)
    generated_at = models.DateTimeField("généré le", null=True, blank=True)
    sent_at = models.DateTimeField("transmis le", null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="créé par", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="periodic_reports",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "rapport périodique"
        verbose_name_plural = "rapports périodiques"
        ordering = ("-period_end", "-created_at")
        indexes = [
            models.Index(fields=("project", "-period_end")),
            models.Index(fields=("status", "-created_at")),
        ]

    def __str__(self) -> str:
        return f"{self.title} — {self.project.reference}"

    def build_snapshot(self) -> dict:
        """Construit les indicateurs de la période à partir des données réelles."""
        from django.db.models import Avg, Count, Q

        from apps.construction.models import PhaseStatus
        from apps.evidences.models import EvidenceStatus

        reports = self.project.daily_reports.filter(
            report_date__gte=self.period_start, report_date__lte=self.period_end
        )
        aggregates = reports.aggregate(
            days=Count("id"),
            avg_workers=Avg("workers_count"),
            blockers=Count("id", filter=~Q(blockers="")),
        )
        phases = self.project.phases.aggregate(
            total=Count("id"),
            done=Count("id", filter=Q(status=PhaseStatus.DONE)),
            blocked=Count("id", filter=Q(status=PhaseStatus.BLOCKED)),
        )
        evidences = self.project.evidences.filter(
            created_at__date__gte=self.period_start, created_at__date__lte=self.period_end
        ).aggregate(
            total=Count("id"),
            validated=Count("id", filter=Q(status=EvidenceStatus.VALIDATED)),
        )
        snapshot = {
            "days_reported": aggregates["days"] or 0,
            "average_workers": round(float(aggregates["avg_workers"] or 0), 1),
            "days_with_blockers": aggregates["blockers"] or 0,
            "phases_total": phases["total"] or 0,
            "phases_done": phases["done"] or 0,
            "phases_blocked": phases["blocked"] or 0,
            "evidences_total": evidences["total"] or 0,
            "evidences_validated": evidences["validated"] or 0,
            "physical_progress": float(self.project.physical_progress),
            "budget_used_percent": self.project.budget_used_percent,
            **self.project.snapshot_metrics(),
        }
        self.progress_snapshot = snapshot
        return snapshot
