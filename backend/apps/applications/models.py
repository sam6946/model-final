"""Candidatures des entreprises BTP aux opportunités publiées.

Chaque candidature est horodatée, qualifiée et notée par l'équipe KEMTA afin
que le client final reçoive une short-list argumentée et non un tas de dossiers.
"""
from __future__ import annotations

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from common.models import ReferenceCounter


class ApplicationStatus(models.TextChoices):
    SUBMITTED = "SUBMITTED", "Candidature reçue"
    REVIEWING = "REVIEWING", "En cours d'examen"
    SHORTLISTED = "SHORTLISTED", "Présélectionnée"
    INTERVIEW = "INTERVIEW", "Entretien / visite programmée"
    AWARDED = "AWARDED", "Retenue"
    REJECTED = "REJECTED", "Non retenue"
    WITHDRAWN = "WITHDRAWN", "Retirée par l'entreprise"


class Application(models.Model):
    """Dossier de candidature d'une entreprise à une opportunité."""

    reference = models.CharField("référence", max_length=40, unique=True)
    opportunity = models.ForeignKey(
        "opportunities.Opportunity", verbose_name="opportunité", on_delete=models.CASCADE,
        related_name="applications",
    )
    company = models.ForeignKey(
        "companies.Company", verbose_name="entreprise", on_delete=models.CASCADE,
        related_name="applications",
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="déposée par", on_delete=models.PROTECT,
        related_name="submitted_applications",
    )

    presentation = models.TextField("présentation de l'entreprise et motivation")
    similar_experience = models.TextField("expériences similaires", blank=True)
    methodology = models.TextField("méthodologie et organisation prévues", blank=True)
    estimated_budget_xaf = models.DecimalField(
        "budget estimatif (FCFA)", max_digits=14, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)],
    )
    proposed_duration_days = models.PositiveIntegerField("délai proposé (jours)", null=True, blank=True)
    team_size = models.PositiveSmallIntegerField("effectif mobilisable", null=True, blank=True)
    team_composition = models.CharField("composition de l'équipe", max_length=255, blank=True)
    message = models.TextField("message complémentaire", blank=True)
    accepts_site_visit = models.BooleanField("accepte une visite de site", default=True)
    contact_override = models.CharField("contact pour ce dossier", max_length=180, blank=True)

    relevant_realizations = models.ManyToManyField(
        "btp_catalog.Realization", verbose_name="réalisations pertinentes",
        related_name="applications", blank=True,
    )

    status = models.CharField(
        "statut", max_length=16, choices=ApplicationStatus.choices,
        default=ApplicationStatus.SUBMITTED, db_index=True,
    )
    score = models.DecimalField(
        "note d'évaluation", max_digits=4, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    internal_notes = models.TextField("notes internes KEMTA", blank=True)
    client_feedback = models.TextField("retour du client", blank=True)
    rejection_reason = models.CharField("motif de non-retenue", max_length=255, blank=True)

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="instruite par", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="reviewed_applications",
    )
    reviewed_at = models.DateTimeField("instruite le", null=True, blank=True)
    decided_at = models.DateTimeField("décision le", null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "candidature BTP"
        verbose_name_plural = "candidatures BTP"
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("opportunity", "company"), name="uniq_application_per_company"
            ),
        ]
        indexes = [
            models.Index(fields=("status", "-created_at")),
            models.Index(fields=("company", "-created_at")),
            models.Index(fields=("opportunity", "status")),
        ]

    def __str__(self) -> str:
        return f"{self.reference} — {self.company.name}"

    def save(self, *args, **kwargs) -> None:
        if not self.reference:
            self.reference = ReferenceCounter.next_reference("CAN", width=5)
        super().save(*args, **kwargs)

    @property
    def is_decided(self) -> bool:
        return self.status in {
            ApplicationStatus.AWARDED,
            ApplicationStatus.REJECTED,
            ApplicationStatus.WITHDRAWN,
        }

    @property
    def status_is_positive(self) -> bool:
        return self.status in {
            ApplicationStatus.SHORTLISTED,
            ApplicationStatus.INTERVIEW,
            ApplicationStatus.AWARDED,
        }


class ApplicationDocument(models.Model):
    """Pièce jointe à une candidature (devis, planning, attestation)."""

    class DocumentKind(models.TextChoices):
        QUOTE = "QUOTE", "Devis estimatif"
        SCHEDULE = "SCHEDULE", "Planning prévisionnel"
        REFERENCE = "REFERENCE", "Attestation de référence"
        TECHNICAL = "TECHNICAL", "Note technique"
        ADMIN = "ADMIN", "Document administratif"
        OTHER = "OTHER", "Autre"

    application = models.ForeignKey(
        Application, verbose_name="candidature", on_delete=models.CASCADE, related_name="documents"
    )
    kind = models.CharField("type", max_length=16, choices=DocumentKind.choices, default=DocumentKind.OTHER)
    title = models.CharField("intitulé", max_length=180, blank=True)
    asset = models.ForeignKey(
        "common.Asset", verbose_name="fichier", on_delete=models.PROTECT, related_name="application_documents"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "pièce de candidature"
        verbose_name_plural = "pièces de candidature"
        ordering = ("kind", "id")

    def __str__(self) -> str:
        return f"{self.get_kind_display()} — {self.application.reference}"
