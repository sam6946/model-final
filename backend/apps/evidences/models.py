"""Preuves terrain : la raison d'être de KEMTA.

Une preuve est une observation datée et localisée du chantier (photo, vidéo,
note vocale transcrite, document). Elle est :

- **horodatée côté serveur** (``created_at``) en plus de la date de prise de vue
  déclarée par le terrain — un client ne doit jamais douter de la fraîcheur ;
- **géolocalisée** quand l'appareil le permet, avec la distance au site connue ;
- **idempotente** grâce à ``client_uuid`` : un téléphone qui renvoie trois fois
  la même photo hors ligne ne crée qu'une seule preuve ;
- **validée** par un superviseur avant d'être publiée au client, selon le niveau
  de contrôle choisi (KEMTA reste maître de la chaîne de confiance).
"""
from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.projects.models import Project


model_property = property  # le champ « property » du modèle masque le décorateur natif

class EvidenceStatus(models.TextChoices):
    PENDING = "PENDING", "En attente de validation"
    VALIDATED = "VALIDATED", "Validée"
    REJECTED = "REJECTED", "Refusée"
    ARCHIVED = "ARCHIVED", "Archivée"


class EvidenceKind(models.TextChoices):
    PHOTO = "PHOTO", "Photo"
    VIDEO = "VIDEO", "Vidéo"
    DOCUMENT = "DOCUMENT", "Document"
    NOTE = "NOTE", "Note de terrain"
    MEASUREMENT = "MEASUREMENT", "Relevé / mesure"
    INCIDENT = "INCIDENT", "Incident"


class Evidence(models.Model):
    """Observation de terrain rattachée à un chantier (ou à une propriété)."""

    project = models.ForeignKey(
        Project, verbose_name="projet", null=True, blank=True,
        on_delete=models.CASCADE, related_name="evidences",
    )
    property = models.ForeignKey(
        "properties.Property", verbose_name="propriété", null=True, blank=True,
        on_delete=models.CASCADE, related_name="evidences",
    )
    phase = models.ForeignKey(
        "construction.Phase", verbose_name="phase", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="evidences",
    )
    task = models.ForeignKey(
        "projects.Task", verbose_name="tâche", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="evidences",
    )
    kind = models.CharField("type", max_length=12, choices=EvidenceKind.choices, default=EvidenceKind.PHOTO)
    title = models.CharField("titre", max_length=180, blank=True)
    caption = models.CharField("légende", max_length=255, blank=True)
    note = models.TextField("observation", blank=True)
    asset = models.ForeignKey(
        "common.Asset", verbose_name="fichier", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="evidences",
    )
    measurements = models.JSONField("relevés", default=dict, blank=True)

    # Provenance : capturée sur le terrain ou téléversée depuis le bureau.
    captured_at = models.DateTimeField("prise le (appareil)", null=True, blank=True)
    captured_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="capturée par", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="captured_evidences",
    )
    capture_device = models.CharField("appareil", max_length=120, blank=True)
    latitude = models.DecimalField("latitude", max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField("longitude", max_digits=9, decimal_places=6, null=True, blank=True)
    accuracy_meters = models.PositiveIntegerField("précision GPS (m)", null=True, blank=True)
    distance_to_site_m = models.PositiveIntegerField("distance au site (m)", null=True, blank=True)
    is_offline_capture = models.BooleanField("capturée hors ligne", default=False)

    # Idempotence de synchronisation (PWA terrain)
    client_uuid = models.UUIDField("identifiant client", default=uuid.uuid4, unique=True, editable=False)

    status = models.CharField(
        "statut", max_length=12, choices=EvidenceStatus.choices, default=EvidenceStatus.PENDING, db_index=True
    )
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="validée par", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="validated_evidences",
    )
    validated_at = models.DateTimeField("validée le", null=True, blank=True)
    rejection_reason = models.CharField("motif de refus", max_length=255, blank=True)
    is_visible_to_customer = models.BooleanField("visible par le client", default=True)
    is_pinned = models.BooleanField("mise en avant", default=False)

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="déposée par", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="uploaded_evidences",
    )
    created_at = models.DateTimeField("reçue le", auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "preuve terrain"
        verbose_name_plural = "preuves terrain"
        ordering = ("-captured_at", "-created_at")
        indexes = [
            models.Index(fields=("project", "status", "-created_at")),
            models.Index(fields=("project", "kind")),
            models.Index(fields=("property", "-created_at")),
            models.Index(fields=("status", "-created_at")),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(project__isnull=False) | models.Q(property__isnull=False),
                name="evidence_requires_project_or_property",
            ),
        ]

    def __str__(self) -> str:
        target = self.project.reference if self.project_id else f"propriété {self.property_id}"
        return f"{self.get_kind_display()} — {target}"

    # -- Affichage --------------------------------------------------------
    @model_property
    def effective_capture_date(self) -> timezone.datetime:
        return self.captured_at or self.created_at

    @model_property
    def is_validated(self) -> bool:
        return self.status == EvidenceStatus.VALIDATED

    @model_property
    def is_pending(self) -> bool:
        return self.status == EvidenceStatus.PENDING

    @model_property
    def preview_url(self) -> str:
        if not self.asset_id:
            return ""
        return self.asset.medium_url

    @model_property
    def thumbnail_url(self) -> str:
        if not self.asset_id:
            return ""
        return self.asset.thumbnail_url

    @model_property
    def has_location(self) -> bool:
        return self.latitude is not None and self.longitude is not None

    @model_property
    def freshness_label(self) -> str:
        """Libellé lisible : « aujourd'hui à 14 h 05 », « il y a 3 jours »."""
        from django.utils.timesince import timesince

        moment = self.effective_capture_date
        if timezone.localdate(moment) == timezone.localdate():
            return f"aujourd'hui à {timezone.localtime(moment).strftime('%H:%M')}"
        return f"il y a {timesince(moment).split(',')[0]}"

    # -- Cycle de vie -----------------------------------------------------
    def validate_by(self, user, *, comment: str = "") -> None:
        self.status = EvidenceStatus.VALIDATED
        self.validated_by = user
        self.validated_at = timezone.now()
        self.rejection_reason = ""
        self.save(update_fields=["status", "validated_by", "validated_at", "rejection_reason", "updated_at"])
        if comment and self.project_id:
            self.project.log_update(
                author=user,
                message=comment,
                update_type="EVIDENCE",
                payload={"evidence_id": self.pk, "status": "VALIDATED"},
            )

    def reject_by(self, user, *, reason: str) -> None:
        self.status = EvidenceStatus.REJECTED
        self.validated_by = user
        self.validated_at = timezone.now()
        self.rejection_reason = reason[:255]
        self.save(update_fields=["status", "validated_by", "validated_at", "rejection_reason", "updated_at"])

    def compute_distance_to_site(self) -> int | None:
        """Distance approximative entre la photo et le site (contrôle de sérieux).

        Calcul de Haversine : suffisant pour détecter une preuve prise à
        plusieurs kilomètres du chantier (alerte de contrôle qualité).
        """
        import math

        target_project = self.project
        if not target_project or target_project.latitude is None or not self.has_location:
            return None
        lat1, lon1 = float(self.latitude), float(self.longitude)
        lat2, lon2 = float(target_project.latitude), float(target_project.longitude)
        radius = 6371000
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        a = (
            math.sin(delta_phi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        )
        distance = int(2 * radius * math.asin(math.sqrt(a)))
        Evidence.objects.filter(pk=self.pk).update(distance_to_site_m=distance)
        self.distance_to_site_m = distance
        return distance

    @model_property
    def is_location_suspect(self) -> bool:
        return bool(self.distance_to_site_m and self.distance_to_site_m > 1500)


class EvidenceComment(models.Model):
    """Échange autour d'une preuve (question du client, réponse du terrain)."""

    evidence = models.ForeignKey(
        Evidence, verbose_name="preuve", on_delete=models.CASCADE, related_name="comments"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="auteur", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="evidence_comments",
    )
    body = models.TextField("message")
    is_internal = models.BooleanField("note interne KEMTA", default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "commentaire de preuve"
        verbose_name_plural = "commentaires de preuve"
        ordering = ("created_at",)
        indexes = [models.Index(fields=("evidence", "created_at"))]

    def __str__(self) -> str:
        return f"{self.author_id} → {self.evidence_id}"
