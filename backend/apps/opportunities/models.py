"""Opportunités BTP : marchés publiés par KEMTA ou par des clients.

Ce sont des appels à candidature : les entreprises vérifiées peuvent postuler.
L'affichage public est volontairement limité (jamais de coordonnées privées du
client, jamais de budget détaillé avant mise en relation).
"""
from __future__ import annotations

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from common.constants import Country
from common.utils import slugify


class OpportunityStatus(models.TextChoices):
    DRAFT = "DRAFT", "Brouillon"
    OPEN = "OPEN", "Ouverte aux candidatures"
    CLOSED = "CLOSED", "Clôturée"
    REVIEWING = "REVIEWING", "En cours d'analyse"
    AWARDED = "AWARDED", "Attribuée"
    CANCELLED = "CANCELLED", "Annulée"


class OpportunityVisibility(models.TextChoices):
    PUBLIC = "PUBLIC", "Visible par tous"
    REGISTERED = "REGISTERED", "Réservée aux entreprises inscrites"
    VERIFIED = "VERIFIED", "Réservée aux entreprises vérifiées"
    INVITED = "INVITED", "Sur invitation KEMTA"


class Opportunity(models.Model):
    """Marché proposé aux entreprises BTP du réseau KEMTA."""

    reference = models.CharField("référence", max_length=40, unique=True)
    title = models.CharField("intitulé du marché", max_length=200)
    slug = models.SlugField("adresse", max_length=220, unique=True)
    description = models.TextField("description du besoin")
    scope_of_work = models.TextField("travaux attendus", blank=True)
    required_documents = models.JSONField("pièces demandées", default=list, blank=True)

    property_type = models.CharField(
        "type de bien",
        max_length=40,
        choices=[
            ("VILLA", "Villa"), ("MAISON", "Maison"), ("IMMEUBLE", "Immeuble"),
            ("APPARTEMENT", "Appartements"), ("LOCAL_COMMERCIAL", "Local commercial"),
            ("ECOLE", "École"), ("SANTE", "Structure de santé"), ("ROUTE", "Voirie"),
            ("FORAGE", "Forage / eau"), ("RENOVATION", "Rénovation"),
            ("AMENAGEMENT", "Aménagement"), ("AUTRE", "Autre"),
        ],
        default="VILLA",
    )
    location = models.ForeignKey(
        "common.Location", verbose_name="localisation", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="opportunities",
    )
    location_text = models.CharField("localisation affichée", max_length=180, blank=True)
    country = models.CharField("pays", max_length=2, choices=Country.choices, default=Country.CM)
    site_available_for_visit = models.BooleanField("visite du site possible", default=True)

    budget_min_xaf = models.DecimalField(
        "budget indicatif minimum (FCFA)", max_digits=14, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)],
    )
    budget_max_xaf = models.DecimalField(
        "budget indicatif maximum (FCFA)", max_digits=14, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)],
    )
    budget_visible = models.BooleanField("afficher le budget indicatif", default=True)

    start_date = models.DateField("démarrage souhaité", null=True, blank=True)
    duration_days = models.PositiveIntegerField("durée estimée (jours)", null=True, blank=True)
    application_deadline = models.DateField("date limite de candidature", db_index=True)

    required_specialties = models.ManyToManyField(
        "companies.Specialty", verbose_name="corps d'état requis", related_name="opportunities", blank=True
    )
    minimum_experience_years = models.PositiveSmallIntegerField("expérience minimale (années)", default=0)
    requires_verified_company = models.BooleanField("réservée aux entreprises vérifiées", default=True)

    status = models.CharField(
        "statut", max_length=16, choices=OpportunityStatus.choices,
        default=OpportunityStatus.DRAFT, db_index=True,
    )
    visibility = models.CharField(
        "visibilité", max_length=16, choices=OpportunityVisibility.choices,
        default=OpportunityVisibility.PUBLIC,
    )
    is_featured = models.BooleanField("mise en avant", default=False)

    published_at = models.DateTimeField("publiée le", null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="créée par", on_delete=models.PROTECT, related_name="created_opportunities"
    )
    project = models.ForeignKey(
        "projects.Project", verbose_name="projet lié", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="opportunities",
    )
    client_name = models.CharField("client (interne)", max_length=180, blank=True)
    client_contact = models.CharField("contact client (interne)", max_length=180, blank=True)
    internal_notes = models.TextField("notes internes", blank=True)

    applications_count = models.PositiveIntegerField("candidatures reçues", default=0)
    views_count = models.PositiveIntegerField("vues", default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "opportunité BTP"
        verbose_name_plural = "opportunités BTP"
        ordering = ("-is_featured", "-published_at", "-created_at")
        indexes = [
            models.Index(fields=("status", "application_deadline")),
            models.Index(fields=("status", "visibility", "-published_at")),
            models.Index(fields=("property_type", "status")),
        ]

    def __str__(self) -> str:
        return f"{self.reference} — {self.title}"

    def save(self, *args, **kwargs) -> None:
        if not self.reference:
            from common.models import ReferenceCounter

            self.reference = ReferenceCounter.next_reference("OPP", width=5)
        if not self.slug:
            base = slugify(f"{self.title}-{self.reference}")
            candidate = base
            suffix = 2
            while Opportunity.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                candidate = f"{base}-{suffix}"
                suffix += 1
            self.slug = candidate
        super().save(*args, **kwargs)

    # -- Affichage --------------------------------------------------------
    @property
    def display_location(self) -> str:
        if self.location_text:
            return self.location_text
        return self.location.label if self.location_id else ""

    @property
    def is_open(self) -> bool:
        from django.utils import timezone

        return (
            self.status == OpportunityStatus.OPEN
            and self.application_deadline >= timezone.localdate()
        )

    @property
    def days_left(self) -> int:
        from django.utils import timezone

        return max(0, (self.application_deadline - timezone.localdate()).days)

    @property
    def budget_label(self) -> str:
        if not self.budget_visible:
            return "Budget communiqué après qualification"
        from common.utils import humanize_amount

        if self.budget_min_xaf and self.budget_max_xaf:
            return f"{humanize_amount(self.budget_min_xaf)} – {humanize_amount(self.budget_max_xaf)}"
        if self.budget_max_xaf:
            return f"jusqu'à {humanize_amount(self.budget_max_xaf)}"
        if self.budget_min_xaf:
            return f"à partir de {humanize_amount(self.budget_min_xaf)}"
        return "Budget à préciser"

    def register_view(self) -> None:
        Opportunity.objects.filter(pk=self.pk).update(views_count=models.F("views_count") + 1)
