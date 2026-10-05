"""Catalogue professionnel : réalisations des entreprises BTP.

Une réalisation est la vitrine commerciale d'une entreprise : elle prouve le
savoir-faire. Elle est donc structurée (type, surface, année, services, budget
optionnel) et illustrée par des médias ordonnés, y compris des avant/après.
"""
from __future__ import annotations

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from common.constants import Country
from common.utils import slugify


class RealizationType(models.TextChoices):
    VILLA = "VILLA", "Villa"
    MAISON = "MAISON", "Maison individuelle"
    IMMEUBLE = "IMMEUBLE", "Immeuble"
    APPARTEMENT = "APPARTEMENT", "Immeuble d'appartements"
    LOCAL_COMMERCIAL = "LOCAL_COMMERCIAL", "Local commercial"
    BUREAU = "BUREAU", "Bureaux"
    ECOLE = "ECOLE", "Établissement scolaire"
    SANTE = "SANTE", "Structure de santé"
    ROUTE = "ROUTE", "Voirie / route"
    FORAGE = "FORAGE", "Forage / adduction d'eau"
    RENOVATION = "RENOVATION", "Rénovation"
    AMENAGEMENT = "AMENAGEMENT", "Aménagement / VRD"
    AUTRE = "AUTRE", "Autre"


class RealizationStatus(models.TextChoices):
    DRAFT = "DRAFT", "Brouillon"
    PENDING = "PENDING", "En attente de validation"
    PUBLISHED = "PUBLISHED", "Publiée"
    REJECTED = "REJECTED", "Refusée"
    ARCHIVED = "ARCHIVED", "Archivée"


class Realization(models.Model):
    """Réalisation publiée dans le catalogue d'une entreprise."""

    company = models.ForeignKey(
        "companies.Company", verbose_name="entreprise", on_delete=models.CASCADE,
        related_name="realizations",
    )
    title = models.CharField("nom de la réalisation", max_length=180)
    slug = models.SlugField("adresse", max_length=220)
    realization_type = models.CharField(
        "type", max_length=24, choices=RealizationType.choices, default=RealizationType.VILLA
    )
    location = models.ForeignKey(
        "common.Location", verbose_name="localisation", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="realizations",
    )
    location_text = models.CharField("localisation affichée", max_length=180, blank=True)
    country = models.CharField("pays", max_length=2, choices=Country.choices, default=Country.CM)
    year = models.PositiveSmallIntegerField("année de livraison", null=True, blank=True)
    description = models.TextField("description", blank=True)
    surface_m2 = models.DecimalField(
        "surface (m²)", max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)],
    )
    levels_count = models.PositiveSmallIntegerField("nombre de niveaux", null=True, blank=True)
    rooms_count = models.PositiveSmallIntegerField("nombre de pièces", null=True, blank=True)
    duration_days = models.PositiveIntegerField("durée des travaux (jours)", null=True, blank=True)
    budget_xaf = models.DecimalField(
        "budget (FCFA)", max_digits=14, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)],
        help_text="Laisser vide si l'entreprise ne souhaite pas publier le budget.",
    )
    budget_visible = models.BooleanField("afficher le budget publiquement", default=False)
    client_testimonial = models.TextField("témoignage client", blank=True)
    client_name = models.CharField("client (affiché si autorisé)", max_length=160, blank=True)
    services = models.ManyToManyField(
        "companies.Specialty", verbose_name="services réalisés", related_name="realizations", blank=True
    )
    cover = models.ForeignKey(
        "common.Asset", verbose_name="photo principale", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="realization_covers",
    )
    status = models.CharField(
        "statut", max_length=20, choices=RealizationStatus.choices,
        default=RealizationStatus.PUBLISHED, db_index=True,
    )
    is_featured = models.BooleanField("mise en avant", default=False)
    views_count = models.PositiveIntegerField("vues", default=0)
    order = models.PositiveIntegerField("ordre", default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="créée par", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "réalisation"
        verbose_name_plural = "réalisations"
        ordering = ("order", "-year", "-created_at")
        constraints = [
            models.UniqueConstraint(fields=("company", "slug"), name="uniq_realization_slug_per_company"),
        ]
        indexes = [
            models.Index(fields=("status", "is_featured", "-year")),
            models.Index(fields=("realization_type", "status")),
            models.Index(fields=("company", "status")),
        ]

    def __str__(self) -> str:
        return f"{self.title} — {self.company.name}"

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            base = slugify(f"{self.title}")
            candidate = base
            suffix = 2
            while (
                Realization.objects.filter(company_id=self.company_id, slug=candidate)
                .exclude(pk=self.pk)
                .exists()
            ):
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
    def cover_url(self) -> str:
        return self.cover.medium_url if self.cover_id else ""

    @property
    def sorted_media(self):
        return self.media.all().order_by("order", "id")

    @property
    def photos(self):
        return [item for item in self.sorted_media if item.kind == RealizationMedia.MediaKind.PHOTO]

    @property
    def before_after(self) -> dict[str, list]:
        """Regroupe les médias avant/après pour l'affichage comparatif."""
        items = list(self.sorted_media)
        return {
            "before": [item for item in items if item.kind == RealizationMedia.MediaKind.BEFORE],
            "after": [item for item in items if item.kind == RealizationMedia.MediaKind.AFTER],
        }

    def register_view(self) -> None:
        Realization.objects.filter(pk=self.pk).update(views_count=models.F("views_count") + 1)


class RealizationMedia(models.Model):
    """Photo, vidéo ou couple avant/après d'une réalisation."""

    class MediaKind(models.TextChoices):
        PHOTO = "PHOTO", "Photo"
        BEFORE = "BEFORE", "Avant travaux"
        AFTER = "AFTER", "Après travaux"
        VIDEO = "VIDEO", "Vidéo"
        PLAN = "PLAN", "Plan / schéma"

    realization = models.ForeignKey(
        Realization, verbose_name="réalisation", on_delete=models.CASCADE, related_name="media"
    )
    kind = models.CharField("type", max_length=10, choices=MediaKind.choices, default=MediaKind.PHOTO)
    asset = models.ForeignKey(
        "common.Asset", verbose_name="fichier", on_delete=models.CASCADE, related_name="realization_media"
    )
    caption = models.CharField("légende", max_length=180, blank=True)
    order = models.PositiveIntegerField("ordre", default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "média de réalisation"
        verbose_name_plural = "médias de réalisation"
        ordering = ("order", "id")
        indexes = [models.Index(fields=("realization", "kind", "order"))]

    def __str__(self) -> str:
        return f"{self.get_kind_display()} — {self.realization.title}"
