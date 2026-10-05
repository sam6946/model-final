"""Demandes de service : point d'entrée commercial de KEMTA.

Une demande arrive soit d'un visiteur non inscrit (le cas le plus fréquent :
un propriétaire de la diaspora remplit le formulaire depuis l'étranger), soit
d'un client connecté. Elle est qualifiée par l'équipe KEMTA, puis convertie en
projet ou en contrat d'entretien.

Le contenu du formulaire est dynamique (les étapes changent selon le service
choisi) : il est donc stocké dans un champ JSON structuré, validé par un
serializer dédié côté API, doublé des champs clés indexés pour le filtrage.
"""
from __future__ import annotations

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from common.constants import Country
from common.models import ReferenceCounter


class ServiceKind(models.TextChoices):
    BUILD_PROJECT = "BUILD_PROJECT", "Construire un projet"
    EXISTING_SITE = "EXISTING_SITE", "Suivre un chantier existant"
    MAINTENANCE = "MAINTENANCE", "Entretenir une propriété"
    OTHER = "OTHER", "Autre besoin"


class RequestStatus(models.TextChoices):
    NEW = "NEW", "Nouvelle"
    REVIEWING = "REVIEWING", "En cours d'étude"
    QUALIFIED = "QUALIFIED", "Qualifiée"
    CONTACTED = "CONTACTED", "Client contacté"
    MEETING = "MEETING", "Rendez-vous programmé"
    CONVERTED = "CONVERTED", "Convertie en projet"
    REJECTED = "REJECTED", "Non retenue"
    CLOSED = "CLOSED", "Clôturée"


class ServiceCatalog(models.Model):
    """Service commercialisable, administrable sans redéploiement.

    Permet à KEMTA de faire évoluer son offre (prix, délais, livrables) et
    alimente la landing page ainsi que les listes de choix des formulaires.
    """

    code = models.SlugField("code", max_length=60, unique=True)
    name = models.CharField("nom du service", max_length=140)
    tagline = models.CharField("accroche", max_length=220, blank=True)
    description = models.TextField("description", blank=True)
    icon = models.CharField("icône", max_length=40, blank=True)
    hero_image = models.ForeignKey(
        "common.Asset", verbose_name="visuel", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="service_heroes",
    )
    deliverables = models.JSONField("livrables", default=list, blank=True)
    base_price_xaf = models.DecimalField(
        "à partir de (FCFA)", max_digits=12, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)],
    )
    duration_days = models.PositiveIntegerField("durée indicative (jours)", null=True, blank=True)
    requires_site_visit = models.BooleanField("visite de site nécessaire", default=True)
    order = models.PositiveIntegerField("ordre", default=0)
    is_active = models.BooleanField("actif", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "service KEMTA"
        verbose_name_plural = "services KEMTA"
        ordering = ("order", "name")
        indexes = [models.Index(fields=("is_active", "order"))]

    def __str__(self) -> str:
        return self.name


class ServiceRequest(models.Model):
    """Demande de service (construire / suivre / entretenir / autre)."""

    reference = models.CharField("référence", max_length=40, unique=True)
    kind = models.CharField("service demandé", max_length=20, choices=ServiceKind.choices, db_index=True)
    service = models.ForeignKey(
        ServiceCatalog, verbose_name="service catalogue", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="requests",
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="client", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="service_requests",
    )

    # Coordonnées à la soumission : conservées telles quelles même si le client
    # crée ensuite un compte (traçabilité commerciale et relance).
    first_name = models.CharField("prénom", max_length=80)
    last_name = models.CharField("nom", max_length=80)
    phone = models.CharField("téléphone", max_length=20, db_index=True)
    email = models.EmailField("e-mail (facultatif)", blank=True)
    country = models.CharField("pays", max_length=2, choices=Country.choices, default=Country.CM)
    city = models.CharField("ville", max_length=120, blank=True)
    city_of_residence = models.CharField("ville de résidence", max_length=120, blank=True)

    project_type = models.CharField("type de projet", max_length=80, blank=True)
    location = models.ForeignKey(
        "common.Location", verbose_name="localisation", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="service_requests",
    )
    location_text = models.CharField("localisation saisie", max_length=200, blank=True)
    budget_min_xaf = models.DecimalField(
        "budget minimum (FCFA)", max_digits=14, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)],
    )
    budget_max_xaf = models.DecimalField(
        "budget maximum (FCFA)", max_digits=14, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)],
    )
    spent_xaf = models.DecimalField(
        "budget déjà engagé (FCFA)", max_digits=14, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)],
    )
    desired_start_date = models.DateField("date souhaitée", null=True, blank=True)
    description = models.TextField("description du besoin", blank=True)
    current_progress = models.CharField("niveau d'avancement", max_length=120, blank=True)
    current_company = models.CharField("entreprise actuelle", max_length=180, blank=True)
    site_manager = models.CharField("chef de chantier", max_length=180, blank=True)
    known_issues = models.TextField("problèmes rencontrés", blank=True)
    objective = models.TextField("objectif recherché", blank=True)
    maintenance_services = models.JSONField("prestations souhaitées", default=list, blank=True)
    maintenance_frequency = models.CharField("fréquence souhaitée", max_length=20, blank=True)
    property_type = models.CharField("type de propriété", max_length=40, blank=True)
    property_occupied = models.CharField("propriété occupée", max_length=20, blank=True)
    last_visit_date = models.DateField("dernière visite", null=True, blank=True)

    payload = models.JSONField(
        "réponses du formulaire", default=dict, blank=True,
        help_text="Réponses brutes du formulaire dynamique (multi-étapes).",
    )
    source = models.CharField("origine", max_length=40, default="site")
    utm = models.JSONField("campagne", default=dict, blank=True)

    status = models.CharField(
        "statut", max_length=16, choices=RequestStatus.choices, default=RequestStatus.NEW, db_index=True
    )
    priority = models.PositiveSmallIntegerField("priorité", default=2, help_text="1 = haute, 3 = basse")
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="chargé de suivi", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="assigned_requests",
    )
    internal_notes = models.TextField("notes internes", blank=True)
    estimated_value_xaf = models.DecimalField(
        "valeur estimée (FCFA)", max_digits=14, decimal_places=2, null=True, blank=True
    )
    qualification_notes = models.TextField("notes de qualification", blank=True)
    scheduled_call_at = models.DateTimeField("appel programmé", null=True, blank=True)
    first_contact_at = models.DateTimeField("premier contact", null=True, blank=True)

    converted_project = models.ForeignKey(
        "projects.Project", verbose_name="projet créé", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="source_requests",
    )
    converted_property = models.ForeignKey(
        "properties.Property", verbose_name="propriété enregistrée", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="source_requests",
    )

    created_at = models.DateTimeField("reçue le", auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField("mise à jour le", auto_now=True)

    class Meta:
        verbose_name = "demande de service"
        verbose_name_plural = "demandes de service"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("status", "priority", "-created_at")),
            models.Index(fields=("kind", "status")),
            models.Index(fields=("phone", "-created_at")),
        ]

    def __str__(self) -> str:
        return f"{self.reference} — {self.kind_label}"

    def save(self, *args, **kwargs) -> None:
        if not self.reference:
            self.reference = ReferenceCounter.next_reference("REQ")
        super().save(*args, **kwargs)

    @property
    def kind_label(self) -> str:
        return self.get_kind_display()

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def display_location(self) -> str:
        if self.location_text:
            return self.location_text
        return self.location.label if self.location_id else ""

    @property
    def budget_label(self) -> str:
        from common.utils import humanize_amount

        if self.budget_min_xaf and self.budget_max_xaf:
            return f"{humanize_amount(self.budget_min_xaf)} – {humanize_amount(self.budget_max_xaf)}"
        if self.budget_max_xaf:
            return humanize_amount(self.budget_max_xaf)
        if self.budget_min_xaf:
            return humanize_amount(self.budget_min_xaf)
        return "Budget non précisé"

    @property
    def is_new(self) -> bool:
        return self.status == RequestStatus.NEW

    @property
    def next_step_label(self) -> str:
        mapping = {
            RequestStatus.NEW: "Qualification par l'équipe KEMTA",
            RequestStatus.REVIEWING: "Étude technique en cours",
            RequestStatus.QUALIFIED: "Prise de contact planifiée",
            RequestStatus.CONTACTED: "Échange avec un chargé de suivi",
            RequestStatus.MEETING: "Rendez-vous programmé",
            RequestStatus.CONVERTED: "Projet ouvert, suivi actif",
            RequestStatus.REJECTED: "Dossier non poursuivi",
            RequestStatus.CLOSED: "Dossier clôturé",
        }
        return mapping.get(self.status, "")


class ServiceRequestAttachment(models.Model):
    """Pièce jointe à une demande : photos, plans, documents administratifs."""

    class Category(models.TextChoices):
        PHOTO = "PHOTO", "Photo du site"
        PLAN = "PLAN", "Plan / croquis"
        DOCUMENT = "DOCUMENT", "Document"
        QUOTE = "QUOTE", "Devis existant"

    request = models.ForeignKey(
        ServiceRequest, verbose_name="demande", on_delete=models.CASCADE, related_name="attachments"
    )
    category = models.CharField("catégorie", max_length=12, choices=Category.choices, default=Category.PHOTO)
    asset = models.ForeignKey(
        "common.Asset", verbose_name="fichier", on_delete=models.PROTECT, related_name="request_attachments"
    )
    caption = models.CharField("légende", max_length=180, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "pièce jointe de demande"
        verbose_name_plural = "pièces jointes de demande"
        ordering = ("category", "id")
        indexes = [models.Index(fields=("request", "category"))]

    def __str__(self) -> str:
        return f"{self.get_category_display()} — {self.request.reference}"


class ServiceRequestEvent(models.Model):
    """Journal d'une demande : qui a fait quoi, quand (transparence interne)."""

    request = models.ForeignKey(
        ServiceRequest, verbose_name="demande", on_delete=models.CASCADE, related_name="events"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="auteur", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="request_events",
    )
    from_status = models.CharField("statut précédent", max_length=16, blank=True)
    to_status = models.CharField("nouveau statut", max_length=16, blank=True)
    comment = models.TextField("commentaire", blank=True)
    is_customer_visible = models.BooleanField("visible par le client", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "événement de demande"
        verbose_name_plural = "événements de demande"
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("request", "-created_at"))]

    def __str__(self) -> str:
        return f"{self.request.reference} → {self.to_status or 'note'}"
