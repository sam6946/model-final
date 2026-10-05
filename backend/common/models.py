"""Modèles transverses : géographie, fichiers, configuration, contenus publics."""
from __future__ import annotations

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.utils import timezone

from common.constants import AssetKind, AssetStatus, LocationKind
from common.utils import build_reference, slugify


class Location(models.Model):
    """Ville, quartier ou région. Table de référence mise en cache agressivement."""

    name = models.CharField("nom", max_length=120)
    slug = models.SlugField("slug", max_length=140, unique=True)
    region = models.CharField("région / province", max_length=120, blank=True)
    country = models.CharField("pays", max_length=2, default="CM")
    kind = models.CharField(
        "type", max_length=20, choices=LocationKind.choices, default=LocationKind.CITY
    )
    latitude = models.DecimalField("latitude", max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField("longitude", max_digits=9, decimal_places=6, null=True, blank=True)
    is_active = models.BooleanField("active", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "localisation"
        verbose_name_plural = "localisations"
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(fields=("name", "country", "kind"), name="uniq_location_name"),
        ]
        indexes = [models.Index(fields=("country", "kind", "is_active"))]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_kind_display()})"

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            base = f"{self.name}-{self.country}".lower()
            self.slug = slugify(base)
        super().save(*args, **kwargs)

    @property
    def label(self) -> str:
        return f"{self.name}, {self.region}" if self.region and self.region != self.name else self.name


class Asset(models.Model):
    """Métadonnée d'un fichier stocké en object storage (jamais le binaire en DB).

    Les variantes (thumbnail / medium / large) sont générées par Celery et
    stockées dans ``variants`` sous forme de clés d'objet.
    """

    kind = models.CharField("type", max_length=20, choices=AssetKind.choices, default=AssetKind.IMAGE)
    status = models.CharField(
        "état", max_length=20, choices=AssetStatus.choices, default=AssetStatus.PENDING
    )
    bucket = models.CharField("bucket", max_length=120, blank=True)
    key = models.CharField("clé objet", max_length=400, db_index=True)
    original_filename = models.CharField("nom d'origine", max_length=255, blank=True)
    mime_type = models.CharField("type MIME", max_length=120, blank=True)
    size_bytes = models.PositiveBigIntegerField("taille (octets)", default=0)
    width = models.PositiveIntegerField("largeur", null=True, blank=True)
    height = models.PositiveIntegerField("hauteur", null=True, blank=True)
    checksum = models.CharField("empreinte", max_length=64, blank=True)
    variants = models.JSONField("variantes", default=dict, blank=True)
    metadata = models.JSONField("métadonnées", default=dict, blank=True)
    is_public = models.BooleanField("public", default=False)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="déposé par",
        related_name="assets",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "fichier"
        verbose_name_plural = "fichiers"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("kind", "status")),
            models.Index(fields=("uploaded_by", "-created_at")),
        ]

    def __str__(self) -> str:
        return self.original_filename or self.key

    # -- Variantes --------------------------------------------------------
    def variant_key(self, size: str = "medium") -> str:
        return self.variants.get(size) or self.key

    def variant_url(self, size: str = "medium") -> str:
        from common.storage import object_storage

        return object_storage.url(self.variant_key(size), public=self.is_public)

    @property
    def url(self) -> str:
        return self.variant_url("large")

    @property
    def thumbnail_url(self) -> str:
        return self.variant_url("thumbnail")

    @property
    def medium_url(self) -> str:
        return self.variant_url("medium")

    @property
    def large_url(self) -> str:
        """Alias explicite de `url` : nommage utilisé par les modèles métier."""
        return self.variant_url("large")

    @property
    def is_image(self) -> bool:
        return self.kind == AssetKind.IMAGE

    def mark_ready(self, *, width: int | None = None, height: int | None = None) -> None:
        Asset.objects.filter(pk=self.pk).update(
            status=AssetStatus.READY, width=width, height=height, updated_at=timezone.now()
        )


class ReferenceCounter(models.Model):
    """Compteur transactionnel des références métier (KEMTA-REQ-2026-000124)."""

    prefix = models.CharField("préfixe", max_length=16)
    year = models.PositiveIntegerField("année")
    last_number = models.PositiveIntegerField("dernier numéro", default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "compteur de référence"
        verbose_name_plural = "compteurs de référence"
        constraints = [
            models.UniqueConstraint(fields=("prefix", "year"), name="uniq_reference_counter"),
        ]

    def __str__(self) -> str:
        return f"{self.prefix}-{self.year}={self.last_number}"

    @classmethod
    def next_reference(cls, prefix: str, *, width: int = 6) -> str:
        """Incrémente et renvoie la référence suivante (verrou de ligne)."""
        year = timezone.localdate().year
        with transaction.atomic():
            counter, _created = cls.objects.select_for_update().get_or_create(
                prefix=prefix, year=year
            )
            cls.objects.filter(pk=counter.pk).update(last_number=models.F("last_number") + 1)
            counter.refresh_from_db(fields=["last_number"])
            if counter.last_number % 250 == 0:
                # Trace d'exploitation : évite une croissance silencieuse.
                import logging

                logging.getLogger("kemta.references").info(
                    "reference_sequence_milestone",
                    extra={"prefix": prefix, "year": year, "value": counter.last_number},
                )
        return build_reference(prefix, counter.last_number, year=year, width=width)


class Configuration(models.Model):
    """Paramétrage applicatif modifiable depuis l'administration (mis en cache)."""

    key = models.CharField("clé", max_length=120, unique=True)
    label = models.CharField("libellé", max_length=180, blank=True)
    value = models.JSONField("valeur", default=dict)
    is_public = models.BooleanField("exposé publiquement", default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "paramètre"
        verbose_name_plural = "paramètres"
        ordering = ("key",)

    def __str__(self) -> str:
        return self.key


class FAQItem(models.Model):
    """FAQ de la landing page — modifiable sans redéploiement."""

    category = models.CharField("catégorie", max_length=80, default="Général")
    question = models.CharField("question", max_length=255)
    answer = models.TextField("réponse")
    order = models.PositiveIntegerField("ordre", default=0)
    is_active = models.BooleanField("active", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "question FAQ"
        verbose_name_plural = "FAQ"
        ordering = ("order", "id")
        indexes = [models.Index(fields=("is_active", "order"))]

    def __str__(self) -> str:
        return self.question


class Testimonial(models.Model):
    """Témoignage client (diaspora, propriétaire local, entreprise BTP)."""

    author_name = models.CharField("nom", max_length=120)
    author_role = models.CharField("fonction / contexte", max_length=160, blank=True)
    author_city = models.CharField("ville", max_length=120, blank=True)
    author_country = models.CharField("pays", max_length=2, default="CM")
    quote = models.TextField("témoignage")
    rating = models.PositiveSmallIntegerField("note", default=5, validators=[MinValueValidator(1)])
    photo = models.ForeignKey(
        Asset, verbose_name="photo", null=True, blank=True, on_delete=models.SET_NULL
    )
    project = models.ForeignKey(
        "projects.Project",
        verbose_name="projet lié",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="testimonials",
    )
    is_published = models.BooleanField("publié", default=False)
    order = models.PositiveIntegerField("ordre", default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "témoignage"
        verbose_name_plural = "témoignages"
        ordering = ("order", "-created_at")

    def __str__(self) -> str:
        return f"{self.author_name} — {self.rating}/5"


class TrustStat(models.Model):
    """Chiffre de confiance de la landing page (géré par l'administration)."""

    label = models.CharField("libellé", max_length=120)
    value = models.CharField("valeur affichée", max_length=40)
    hint = models.CharField("précision", max_length=160, blank=True)
    icon = models.CharField("icône", max_length=40, blank=True)
    order = models.PositiveIntegerField("ordre", default=0)
    is_active = models.BooleanField("actif", default=True)

    class Meta:
        verbose_name = "chiffre de confiance"
        verbose_name_plural = "chiffres de confiance"
        ordering = ("order",)

    def __str__(self) -> str:
        return f"{self.value} — {self.label}"


class IdempotencyKey(models.Model):
    """Clé d'idempotence pour les créations sensibles (paiement, preuve offline)."""

    key = models.CharField("clé", max_length=140, unique=True)
    scope = models.CharField("périmètre", max_length=80)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    response_status = models.PositiveSmallIntegerField("statut", default=0)
    response_body = models.JSONField("réponse", default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "clé d'idempotence"
        verbose_name_plural = "clés d'idempotence"
        indexes = [models.Index(fields=("scope", "-created_at"))]

    def __str__(self) -> str:
        return f"{self.scope}:{self.key}"
