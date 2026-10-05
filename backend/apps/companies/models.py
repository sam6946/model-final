"""Entreprises BTP : profil public, vérification KEMTA, documents, avis.

Une entreprise est une entité commerciale distincte de son utilisateur
propriétaire. Plusieurs membres peuvent la représenter (gérant, technicien,
commercial), avec des droits différenciés.
"""
from __future__ import annotations

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from common.constants import CAMEROON_REGIONS, Country
from common.utils import slugify


class VerificationStatus(models.TextChoices):
    DRAFT = "DRAFT", "Brouillon"
    PENDING = "PENDING", "En attente de vérification"
    VERIFIED = "VERIFIED", "Entreprise vérifiée"
    REJECTED = "REJECTED", "Dossier à compléter"
    SUSPENDED = "SUSPENDED", "Suspendue"


class Specialty(models.Model):
    """Métier / corps d'état (maçonnerie, électricité, menuiserie…).

    Table de référence éditable depuis l'administration et mise en cache :
    elle sert au filtrage du catalogue et aux exigences des opportunités.
    """

    code = models.SlugField("code", max_length=60, unique=True)
    name = models.CharField("libellé", max_length=120)
    category = models.CharField("famille", max_length=80, blank=True)
    description = models.CharField("description", max_length=255, blank=True)
    icon = models.CharField("icône", max_length=40, blank=True)
    order = models.PositiveIntegerField("ordre", default=0)
    is_active = models.BooleanField("active", default=True)

    class Meta:
        verbose_name = "corps d'état"
        verbose_name_plural = "corps d'état"
        ordering = ("order", "name")
        indexes = [models.Index(fields=("is_active", "order"))]

    def __str__(self) -> str:
        return self.name


class Company(models.Model):
    """Entreprise BTP référencée sur KEMTA."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="responsable du compte",
        on_delete=models.PROTECT, related_name="owned_companies",
    )
    name = models.CharField("nom commercial", max_length=180)
    slug = models.SlugField("adresse publique", max_length=200, unique=True)
    legal_name = models.CharField("raison sociale", max_length=200, blank=True)
    registration_number = models.CharField("numéro de registre de commerce", max_length=80, blank=True)
    tax_number = models.CharField("numéro contribuable", max_length=80, blank=True)
    phone = models.CharField("téléphone professionnel", max_length=20)
    secondary_phone = models.CharField("second numéro", max_length=20, blank=True)
    email = models.EmailField("e-mail professionnel", blank=True)
    website = models.URLField("site web", blank=True)
    city = models.CharField("ville", max_length=120)
    region = models.CharField("région", max_length=2, choices=CAMEROON_REGIONS, blank=True)
    address = models.CharField("adresse", max_length=255, blank=True)
    country = models.CharField("pays", max_length=2, choices=Country.choices, default=Country.CM)

    description = models.TextField("présentation", blank=True)
    years_experience = models.PositiveSmallIntegerField(
        "années d'expérience", default=0, validators=[MaxValueValidator(80)]
    )
    employees_count = models.PositiveSmallIntegerField("effectif", default=1)
    projects_count = models.PositiveIntegerField("projets réalisés", default=0)
    equipment_summary = models.CharField("moyens techniques", max_length=255, blank=True)

    specialties = models.ManyToManyField(
        Specialty, verbose_name="corps d'état", related_name="companies", blank=True
    )
    intervention_regions = models.JSONField(
        "zones d'intervention", default=list, blank=True,
        help_text="Liste de codes régions ou villes, ex. ['CE', 'LT', 'Yaoundé']",
    )
    intervention_radius_km = models.PositiveIntegerField("rayon d'intervention (km)", default=50)

    logo = models.ForeignKey(
        "common.Asset", verbose_name="logo", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="company_logos",
    )
    cover = models.ForeignKey(
        "common.Asset", verbose_name="photo de couverture", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="company_covers",
    )

    verification_status = models.CharField(
        "statut de vérification", max_length=20, choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING, db_index=True,
    )
    verification_notes = models.TextField("notes de vérification", blank=True)
    verified_at = models.DateTimeField("vérifiée le", null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="vérifiée par", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="verified_companies",
    )
    is_published = models.BooleanField("visible dans le catalogue", default=False)
    is_featured = models.BooleanField("mise en avant", default=False)

    rating_average = models.DecimalField(
        "note moyenne", max_digits=3, decimal_places=2, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
    )
    rating_count = models.PositiveIntegerField("nombre d'avis", default=0)
    completed_projects_count = models.PositiveIntegerField("chantiers suivis via KEMTA", default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "entreprise BTP"
        verbose_name_plural = "entreprises BTP"
        ordering = ("-is_featured", "-rating_average", "name")
        indexes = [
            models.Index(fields=("verification_status", "is_published")),
            models.Index(fields=("city",)),
            models.Index(fields=("slug",)),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            base = slugify(self.name)
            candidate = base
            suffix = 2
            while Company.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                candidate = f"{base}-{suffix}"
                suffix += 1
            self.slug = candidate
        super().save(*args, **kwargs)

    # -- Aides métier -----------------------------------------------------
    @property
    def is_verified(self) -> bool:
        return self.verification_status == VerificationStatus.VERIFIED

    @property
    def public_url(self) -> str:
        return f"/entreprises/{self.slug}"

    @property
    def logo_url(self) -> str:
        return self.logo.medium_url if self.logo_id else ""

    @property
    def cover_url(self) -> str:
        return self.cover.large_url if self.cover_id else ""

    def mark_verified(self, *, by=None, notes: str = "") -> None:
        self.verification_status = VerificationStatus.VERIFIED
        self.verified_at = timezone.now()
        self.verified_by = by
        self.verification_notes = notes
        self.is_published = True
        self.save(update_fields=[
            "verification_status", "verified_at", "verified_by", "verification_notes",
            "is_published", "updated_at",
        ])

    def recalculate_rating(self) -> None:
        """Recalcule la note moyenne (dénormalisée pour le catalogue public)."""
        from django.db.models import Avg, Count

        stats = self.reviews.filter(is_published=True).aggregate(
            avg=Avg("rating"), total=Count("id")
        )
        Company.objects.filter(pk=self.pk).update(
            rating_average=round(stats["avg"] or 0, 2),
            rating_count=stats["total"] or 0,
            updated_at=timezone.now(),
        )


class CompanyMember(models.Model):
    """Membre d'une entreprise avec un rôle défini (RBAC intra-entreprise)."""

    class MemberRole(models.TextChoices):
        OWNER = "OWNER", "Propriétaire"
        MANAGER = "MANAGER", "Gérant"
        EDITOR = "EDITOR", "Éditeur du catalogue"
        FIELD = "FIELD", "Conducteur de travaux"
        VIEWER = "VIEWER", "Observateur"

    company = models.ForeignKey(
        Company, verbose_name="entreprise", on_delete=models.CASCADE, related_name="members"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="utilisateur", on_delete=models.CASCADE,
        related_name="company_memberships",
    )
    role = models.CharField("rôle", max_length=20, choices=MemberRole.choices, default=MemberRole.OWNER)
    job_title = models.CharField("fonction", max_length=120, blank=True)
    can_publish_catalog = models.BooleanField("peut publier au catalogue", default=True)
    is_active = models.BooleanField("actif", default=True)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="invité par", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="company_invitations",
    )
    joined_at = models.DateTimeField("a rejoint le", auto_now_add=True)

    class Meta:
        verbose_name = "membre d'entreprise"
        verbose_name_plural = "membres d'entreprise"
        constraints = [
            models.UniqueConstraint(fields=("company", "user"), name="uniq_company_member"),
        ]
        indexes = [models.Index(fields=("user", "is_active"))]

    def __str__(self) -> str:
        return f"{self.user.full_name} — {self.company.name} ({self.get_role_display()})"

    @property
    def can_manage(self) -> bool:
        return self.role in {self.MemberRole.OWNER, self.MemberRole.MANAGER}


class CompanyDocument(models.Model):
    """Pièces administratives du dossier de vérification."""

    class DocumentKind(models.TextChoices):
        REGISTRE_COMMERCE = "REGISTRE_COMMERCE", "Registre de commerce"
        ATTESTATION_FISCALE = "ATTESTATION_FISCALE", "Attestation de conformité fiscale"
        CNPS = "CNPS", "Attestation CNPS"
        ASSURANCE = "ASSURANCE", "Attestation d'assurance"
        REFERENCE = "REFERENCE", "Référence / attestation de bonne exécution"
        PLAN = "PLAN", "Plan ou devis type"
        OTHER = "OTHER", "Autre document"

    class ReviewStatus(models.TextChoices):
        PENDING = "PENDING", "En attente"
        APPROVED = "APPROVED", "Validé"
        REJECTED = "REJECTED", "Refusé"

    company = models.ForeignKey(
        Company, verbose_name="entreprise", on_delete=models.CASCADE, related_name="documents"
    )
    kind = models.CharField("type", max_length=30, choices=DocumentKind.choices)
    title = models.CharField("intitulé", max_length=180, blank=True)
    asset = models.ForeignKey(
        "common.Asset", verbose_name="fichier", on_delete=models.PROTECT, related_name="company_documents"
    )
    reference_number = models.CharField("numéro du document", max_length=120, blank=True)
    issued_at = models.DateField("date de délivrance", null=True, blank=True)
    expires_at = models.DateField("date d'expiration", null=True, blank=True)
    status = models.CharField("statut", max_length=20, choices=ReviewStatus.choices, default=ReviewStatus.PENDING)
    review_notes = models.CharField("retour KEMTA", max_length=255, blank=True)
    reviewed_at = models.DateTimeField("examiné le", null=True, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "document d'entreprise"
        verbose_name_plural = "documents d'entreprise"
        ordering = ("kind", "-created_at")
        indexes = [models.Index(fields=("company", "status"))]

    def __str__(self) -> str:
        return f"{self.get_kind_display()} — {self.company.name}"

    @property
    def is_expired(self) -> bool:
        return bool(self.expires_at and self.expires_at < timezone.localdate())


class CompanyReview(models.Model):
    """Avis d'un client KEMTA sur une entreprise (modéré avant publication)."""

    company = models.ForeignKey(
        Company, verbose_name="entreprise", on_delete=models.CASCADE, related_name="reviews"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="auteur", on_delete=models.CASCADE, related_name="company_reviews"
    )
    project = models.ForeignKey(
        "projects.Project", verbose_name="projet concerné", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="company_reviews",
    )
    rating = models.PositiveSmallIntegerField(
        "note", validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField("commentaire", blank=True)
    work_quality = models.PositiveSmallIntegerField(
        "qualité d'exécution", null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    deadline_respect = models.PositiveSmallIntegerField(
        "respect des délais", null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    communication = models.PositiveSmallIntegerField(
        "communication", null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    is_published = models.BooleanField("publié", default=False)
    response = models.TextField("réponse de l'entreprise", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "avis entreprise"
        verbose_name_plural = "avis entreprises"
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(fields=("company", "author", "project"), name="uniq_review_per_project"),
        ]
        indexes = [models.Index(fields=("company", "is_published"))]

    def __str__(self) -> str:
        return f"{self.company.name} — {self.rating}/5 par {self.author.full_name}"
