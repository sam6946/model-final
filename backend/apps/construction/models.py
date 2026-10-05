"""Phases de chantier : la structure d'avancement d'un projet.

Les phases portent un **poids** (part du budget/du volume de travaux) : c'est ce
qui permet de calculer un avancement réaliste plutôt qu'une simple moyenne. Un
chantier repris en cours de route peut démarrer avec des phases déjà marquées
terminées, ce qui restitue immédiatement l'état réel.
"""
from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from apps.projects.models import Project


class PhaseStatus(models.TextChoices):
    NOT_STARTED = "NOT_STARTED", "Non démarrée"
    IN_PROGRESS = "IN_PROGRESS", "En cours"
    BLOCKED = "BLOCKED", "Bloquée"
    DONE = "DONE", "Terminée"
    CANCELLED = "CANCELLED", "Annulée"


class Phase(models.Model):
    """Étape d'un chantier (fondations, élévation, toiture, finitions…)."""

    project = models.ForeignKey(
        Project, verbose_name="projet", on_delete=models.CASCADE, related_name="phases"
    )
    name = models.CharField("nom de l'étape", max_length=160)
    description = models.TextField("description", blank=True)
    order = models.PositiveIntegerField("ordre", default=0)
    weight_percent = models.DecimalField(
        "poids dans l'avancement (%)", max_digits=5, decimal_places=2, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Part de cette étape dans le volume global de travaux.",
    )
    progress_percent = models.DecimalField(
        "avancement (%)", max_digits=5, decimal_places=2, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    status = models.CharField(
        "statut", max_length=12, choices=PhaseStatus.choices, default=PhaseStatus.NOT_STARTED, db_index=True
    )
    planned_start = models.DateField("début prévu", null=True, blank=True)
    planned_end = models.DateField("fin prévue", null=True, blank=True)
    actual_start = models.DateField("début effectif", null=True, blank=True)
    actual_end = models.DateField("fin effective", null=True, blank=True)
    budget_planned_xaf = models.DecimalField(
        "budget prévu (FCFA)", max_digits=14, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)],
    )
    budget_spent_xaf = models.DecimalField(
        "dépensé (FCFA)", max_digits=14, decimal_places=2, default=0, validators=[MinValueValidator(0)]
    )
    responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="responsable", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="phases",
    )
    blocked_reason = models.CharField("motif du blocage", max_length=255, blank=True)
    notes = models.TextField("notes", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "phase de chantier"
        verbose_name_plural = "phases de chantier"
        ordering = ("order", "id")
        indexes = [
            models.Index(fields=("project", "order")),
            models.Index(fields=("project", "status")),
        ]
        constraints = [
            models.UniqueConstraint(fields=("project", "name"), name="uniq_phase_name_per_project"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.project.reference})"

    # -- Indicateurs ------------------------------------------------------
    @property
    def is_done(self) -> bool:
        return self.status == PhaseStatus.DONE

    @property
    def is_overdue(self) -> bool:
        return bool(
            self.planned_end
            and self.status not in {PhaseStatus.DONE, PhaseStatus.CANCELLED}
            and self.planned_end < timezone.localdate()
        )

    @property
    def budget_variance_xaf(self) -> Decimal:
        return (self.budget_planned_xaf or Decimal("0")) - (self.budget_spent_xaf or Decimal("0"))

    @property
    def status_label(self) -> str:
        if self.status == PhaseStatus.DONE:
            return "Terminée"
        if self.status == PhaseStatus.BLOCKED:
            return "Bloquée"
        if self.progress_percent and self.progress_percent > 0:
            return f"En cours ({self.progress_percent:.0f} %)"
        return self.get_status_display()

    @property
    def evidences_count(self) -> int:
        return self.evidences.count() if hasattr(self, "evidences") else 0

    # -- Cycle de vie -----------------------------------------------------
    def set_progress(self, value: float, *, actor=None, save: bool = True) -> None:
        """Met à jour l'avancement d'une phase et propage au projet."""
        bounded = max(0.0, min(100.0, float(value)))
        self.progress_percent = Decimal(str(round(bounded, 2)))
        if bounded >= 100:
            self.status = PhaseStatus.DONE
            self.actual_end = self.actual_end or timezone.localdate()
        elif bounded > 0 and self.status in {PhaseStatus.NOT_STARTED, PhaseStatus.DONE}:
            self.status = PhaseStatus.IN_PROGRESS
            self.actual_start = self.actual_start or timezone.localdate()
        if save:
            self.save(update_fields=["progress_percent", "status", "actual_start", "actual_end", "updated_at"])
        self.recalculate_project_progress()

    def recalculate_project_progress(self) -> Decimal:
        return self.project.recalculate_progress()

    def mark_blocked(self, *, reason: str = "", actor=None) -> None:
        self.status = PhaseStatus.BLOCKED
        self.blocked_reason = reason[:255]
        self.save(update_fields=["status", "blocked_reason", "updated_at"])
        self.project.refresh_health()

    def mark_started(self, *, actor=None) -> None:
        self.status = PhaseStatus.IN_PROGRESS
        self.actual_start = self.actual_start or timezone.localdate()
        self.save(update_fields=["status", "actual_start", "updated_at"])

    def mark_done(self, *, actor=None) -> None:
        self.status = PhaseStatus.DONE
        self.progress_percent = Decimal("100")
        self.actual_end = self.actual_end or timezone.localdate()
        self.save(update_fields=["status", "progress_percent", "actual_end", "updated_at"])
        self.recalculate_project_progress()


# Alias pratique : `from apps.construction.models import PhaseStatus` (déjà défini
# plus haut) et `Phase.Template` pour créer un squelette de phases standard.


class PhaseTemplate(models.Model):
    """Modèle d'étapes réutilisable (construction neuve, rénovation, suivi).

    Évite de saisir 12 phases à la main à chaque nouveau chantier, tout en
    laissant l'équipe ajuster le squelette proposé.
    """

    name = models.CharField("nom du modèle", max_length=140, unique=True)
    kind = models.CharField("nature de projet", max_length=16, blank=True)
    description = models.CharField("description", max_length=255, blank=True)
    steps = models.JSONField(
        "étapes", default=list,
        help_text="Liste [{name, weight_percent, duration_days, description}]",
    )
    is_active = models.BooleanField("actif", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "modèle de phases"
        verbose_name_plural = "modèles de phases"
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name

    def apply_to(self, project: Project, *, start_date=None) -> list[Phase]:
        """Crée les phases du modèle sur un projet, en enchaînant les dates."""
        from datetime import timedelta

        created: list[Phase] = []
        cursor = start_date or project.planned_start or timezone.localdate()
        for index, step in enumerate(self.steps or []):
            duration = int(step.get("duration_days") or 7)
            phase = Phase.objects.create(
                project=project,
                name=step.get("name") or f"Étape {index + 1}",
                description=step.get("description", ""),
                order=index,
                weight_percent=Decimal(str(step.get("weight_percent") or 0)),
                planned_start=cursor,
                planned_end=cursor + timedelta(days=duration),
            )
            cursor = cursor + timedelta(days=duration)
            created.append(phase)
        return created
