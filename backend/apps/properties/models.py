"""Propriétés immobilières : le patrimoine du client.

KEMTA ne suit pas seulement des chantiers : il garde aussi un patrimoine. Une
propriété possède un historique d'entretien, des visites de contrôle et des
alertes : c'est ce qui justifie un abonnement récurrent pour un propriétaire
diaspora dont la maison reste vide plusieurs mois par an.
"""
from __future__ import annotations

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from common.constants import Country
from common.models import ReferenceCounter


class PropertyType(models.TextChoices):
    VILLA = "VILLA", "Villa"
    MAISON = "MAISON", "Maison"
    APPARTEMENT = "APPARTEMENT", "Appartement"
    IMMEUBLE = "IMMEUBLE", "Immeuble"
    LOCAL_COMMERCIAL = "LOCAL_COMMERCIAL", "Local commercial"
    BUREAU = "BUREAU", "Bureau"
    TERRAIN = "TERRAIN", "Terrain"
    ENTREPOT = "ENTREPOT", "Entrepôt"


class OccupancyStatus(models.TextChoices):
    VACANT = "VACANT", "Inoccupée"
    OCCUPIED_OWNER = "OCCUPIED_OWNER", "Occupée par le propriétaire"
    RENTED = "RENTED", "Louée"
    FAMILY = "FAMILY", "Occupée par la famille"
    GUARDED = "GUARDED", "Sous gardiennage"
    UNDER_WORK = "UNDER_WORK", "En travaux"


class Property(models.Model):
    """Bien immobilier suivi par KEMTA."""

    reference = models.CharField("référence", max_length=40, unique=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="propriétaire", on_delete=models.PROTECT,
        related_name="properties",
    )
    name = models.CharField("nom du bien", max_length=180)
    property_type = models.CharField("type", max_length=20, choices=PropertyType.choices, default=PropertyType.VILLA)
    location = models.ForeignKey(
        "common.Location", verbose_name="localisation", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="properties",
    )
    location_text = models.CharField("localisation affichée", max_length=200, blank=True)
    address = models.CharField("adresse / repère", max_length=255, blank=True)
    city = models.CharField("ville", max_length=120, blank=True)
    country = models.CharField("pays", max_length=2, choices=Country.choices, default=Country.CM)
    latitude = models.DecimalField("latitude", max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField("longitude", max_digits=9, decimal_places=6, null=True, blank=True)

    area_m2 = models.DecimalField(
        "surface (m²)", max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)],
    )
    land_area_m2 = models.DecimalField(
        "surface du terrain (m²)", max_digits=12, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)],
    )
    rooms_count = models.PositiveSmallIntegerField("nombre de pièces", null=True, blank=True)
    bedrooms_count = models.PositiveSmallIntegerField("chambres", null=True, blank=True)
    bathrooms_count = models.PositiveSmallIntegerField("salles d'eau", null=True, blank=True)
    levels_count = models.PositiveSmallIntegerField("niveaux", null=True, blank=True)
    year_built = models.PositiveSmallIntegerField("année de construction", null=True, blank=True)

    occupancy_status = models.CharField(
        "occupation", max_length=20, choices=OccupancyStatus.choices, default=OccupancyStatus.VACANT
    )
    tenant_name = models.CharField("locataire / occupant", max_length=180, blank=True)
    tenant_phone = models.CharField("téléphone de l'occupant", max_length=20, blank=True)
    has_guardian = models.BooleanField("gardien sur place", default=False)
    is_fenced = models.BooleanField("clôturée", default=False)
    has_water = models.BooleanField("eau courante", default=True)
    has_electricity = models.BooleanField("électricité", default=True)
    has_security_system = models.BooleanField("dispositif de sécurité", default=False)

    documentation_status = models.CharField(
        "situation documentaire", max_length=40, blank=True,
        help_text="Ex. titre foncier disponible, acte de vente, litige en cours.",
    )
    title_deed_number = models.CharField("numéro de titre", max_length=80, blank=True)
    estimated_value_xaf = models.DecimalField(
        "valeur estimée (FCFA)", max_digits=16, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)],
    )
    monthly_rent_xaf = models.DecimalField(
        "loyer mensuel (FCFA)", max_digits=12, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)],
    )

    cover = models.ForeignKey(
        "common.Asset", verbose_name="photo principale", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="property_covers",
    )
    description = models.TextField("description", blank=True)
    internal_notes = models.TextField("notes internes", blank=True)

    last_visited_at = models.DateTimeField("dernière visite", null=True, blank=True)
    last_inspection_at = models.DateTimeField("dernière inspection", null=True, blank=True)
    next_visit_at = models.DateTimeField("prochaine visite planifiée", null=True, blank=True, db_index=True)
    condition_score = models.PositiveSmallIntegerField(
        "état général (sur 100)", null=True, blank=True,
        validators=[MinValueValidator(0)],
        help_text="Note d'état issue de la dernière inspection.",
    )
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="chargé de suivi", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="managed_properties",
    )
    is_active = models.BooleanField("suivi actif", default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "propriété"
        verbose_name_plural = "propriétés"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("owner", "is_active")),
            models.Index(fields=("occupancy_status",)),
            models.Index(fields=("next_visit_at",)),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_property_type_display()})"

    def save(self, *args, **kwargs) -> None:
        if not self.reference:
            self.reference = ReferenceCounter.next_reference("BIEN", width=5)
        super().save(*args, **kwargs)

    # -- Affichage --------------------------------------------------------
    @property
    def display_location(self) -> str:
        if self.location_text:
            return self.location_text
        if self.location_id:
            return self.location.label
        return self.city

    @property
    def is_vacant(self) -> bool:
        return self.occupancy_status in {OccupancyStatus.VACANT, OccupancyStatus.GUARDED}

    @property
    def cover_url(self) -> str:
        return self.cover.medium_url if self.cover_id else ""

    @property
    def days_since_last_visit(self) -> int | None:
        if not self.last_visited_at:
            return None
        return (timezone.now() - self.last_visited_at).days

    @property
    def needs_attention(self) -> bool:
        """Un bien vacant non vu depuis plus de 60 jours est une alerte commerciale."""
        if not self.is_vacant:
            return False
        days = self.days_since_last_visit
        return days is None or days > 60

    @property
    def active_contract(self):
        return self.maintenance_contracts.filter(status="ACTIVE").order_by("-start_date").first()

    def register_visit(self, *, at=None, score: int | None = None) -> None:
        now = at or timezone.now()
        self.last_visited_at = now
        if score is not None:
            self.condition_score = max(0, min(100, int(score)))
        self.save(update_fields=["last_visited_at", "condition_score", "updated_at"])


class PropertyPhoto(models.Model):
    """Galerie photo d'une propriété (état initial, évolution, sinistres)."""

    class PhotoKind(models.TextChoices):
        GENERAL = "GENERAL", "Vue générale"
        INTERIOR = "INTERIOR", "Intérieur"
        ISSUE = "ISSUE", "Problème constaté"
        REPAIR = "REPAIR", "Réparation"
        DOCUMENT = "DOCUMENT", "Document"

    property = models.ForeignKey(
        Property, verbose_name="propriété", on_delete=models.CASCADE, related_name="photos"
    )
    kind = models.CharField("type", max_length=10, choices=PhotoKind.choices, default=PhotoKind.GENERAL)
    asset = models.ForeignKey(
        "common.Asset", verbose_name="fichier", on_delete=models.CASCADE, related_name="property_photos"
    )
    caption = models.CharField("légende", max_length=180, blank=True)
    taken_at = models.DateTimeField("prise le", default=timezone.now)
    order = models.PositiveIntegerField("ordre", default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "photo de propriété"
        verbose_name_plural = "photos de propriété"
        ordering = ("order", "-taken_at")
        indexes = [models.Index(fields=("property", "kind"))]

    def __str__(self) -> str:
        return f"{self.get_kind_display()} — {self.property.name}"
