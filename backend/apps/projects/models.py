"""Projets et chantiers : cœur opérationnel de KEMTA.

Un projet est le dossier de suivi d'un chantier (construction neuve, reprise de
chantier, ou grand entretien). Il agrège :

- l'avancement physique (phases, tâches, preuves terrain) ;
- l'avancement financier (lignes budgétaires, dépenses, factures) ;
- la communication (mises à jour, documents, rapports).

Les indicateurs affichés (avancement, santé, budget consommé) sont calculés à
partir des données sources : aucun compteur n'est stocké « au doigt mouillé ».
"""
from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.utils import timezone

from common.constants import Country, Currency
from common.models import ReferenceCounter
from common.utils import slugify


class ProjectKind(models.TextChoices):
    BUILD = "BUILD", "Construction neuve"
    FOLLOW_UP = "FOLLOW_UP", "Suivi de chantier existant"
    MAINTENANCE = "MAINTENANCE", "Entretien / réhabilitation"
    STUDY = "STUDY", "Étude et faisabilité"


class ProjectStatus(models.TextChoices):
    DRAFT = "DRAFT", "Préparation"
    PLANNING = "PLANNING", "Planification"
    IN_PROGRESS = "IN_PROGRESS", "Travaux en cours"
    ON_HOLD = "ON_HOLD", "Travaux suspendus"
    HANDOVER = "HANDOVER", "Réception en cours"
    COMPLETED = "COMPLETED", "Livré"
    CANCELLED = "CANCELLED", "Annulé"


class HealthStatus(models.TextChoices):
    ON_TRACK = "ON_TRACK", "Dans les délais"
    WATCH = "WATCH", "À surveiller"
    AT_RISK = "AT_RISK", "En difficulté"
    COMPLETED = "COMPLETED", "Terminé"


model_property = property  # le champ « property » du modèle masque le décorateur natif

class Project(models.Model):
    """Dossier de suivi d'un chantier."""

    reference = models.CharField("référence", max_length=40, unique=True)
    name = models.CharField("nom du projet", max_length=200)
    slug = models.SlugField("adresse", max_length=220, unique=True)
    kind = models.CharField("nature", max_length=16, choices=ProjectKind.choices, default=ProjectKind.BUILD)
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="client", on_delete=models.PROTECT,
        related_name="projects",
    )
    request = models.ForeignKey(
        "service_requests.ServiceRequest", verbose_name="demande d'origine", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="projects",
    )
    property = models.ForeignKey(
        "properties.Property", verbose_name="propriété concernée", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="projects",
    )

    # Pilotage KEMTA
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="chargé de suivi KEMTA", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="managed_projects",
    )
    company = models.ForeignKey(
        "companies.Company", verbose_name="entreprise BTP retenue", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="projects",
    )

    # Localisation
    location = models.ForeignKey(
        "common.Location", verbose_name="localisation", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="projects",
    )
    location_text = models.CharField("localisation affichée", max_length=200, blank=True)
    address = models.CharField("adresse / repère", max_length=255, blank=True)
    country = models.CharField("pays", max_length=2, choices=Country.choices, default=Country.CM)
    latitude = models.DecimalField("latitude", max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField("longitude", max_digits=9, decimal_places=6, null=True, blank=True)

    description = models.TextField("description", blank=True)
    cover = models.ForeignKey(
        "common.Asset", verbose_name="photo de couverture", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="project_covers",
    )

    # Avancement et santé
    status = models.CharField(
        "statut", max_length=16, choices=ProjectStatus.choices, default=ProjectStatus.DRAFT, db_index=True
    )
    health = models.CharField(
        "santé du chantier", max_length=12, choices=HealthStatus.choices, default=HealthStatus.ON_TRACK
    )
    health_notes = models.CharField("explication de la santé", max_length=255, blank=True)
    physical_progress = models.DecimalField(
        "avancement physique (%)", max_digits=5, decimal_places=2, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )

    # Budget (le montant est stocké en XAF, devise d'affichage paramétrable)
    currency = models.CharField("devise", max_length=3, choices=Currency.choices, default=Currency.XAF)
    budget_total_xaf = models.DecimalField(
        "budget total (FCFA)", max_digits=16, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)],
    )
    budget_spent_xaf = models.DecimalField(
        "dépenses engagées (FCFA)", max_digits=16, decimal_places=2, default=0,
        validators=[MinValueValidator(0)],
    )
    contract_signed = models.BooleanField("contrat signé", default=False)
    contract_file = models.ForeignKey(
        "common.Asset", verbose_name="contrat", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="project_contracts",
    )

    # Calendrier
    planned_start = models.DateField("démarrage prévu", null=True, blank=True)
    planned_end = models.DateField("livraison prévue", null=True, blank=True)
    actual_start = models.DateField("démarrage effectif", null=True, blank=True)
    actual_end = models.DateField("livraison effective", null=True, blank=True)
    next_visit_at = models.DateTimeField("prochaine visite", null=True, blank=True)

    # Visibilité client (permet de préparer un chantier sans tout exposer)
    customer_can_comment = models.BooleanField("le client peut commenter", default=True)
    is_archived = models.BooleanField("archivé", default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "projet"
        verbose_name_plural = "projets"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("status", "health", "-updated_at")),
            models.Index(fields=("customer", "status")),
            models.Index(fields=("manager", "status")),
            models.Index(fields=("company", "status")),
            models.Index(fields=("slug",)),
        ]

    def __str__(self) -> str:
        return f"{self.reference} — {self.name}"

    def save(self, *args, **kwargs) -> None:
        if not self.reference:
            self.reference = ReferenceCounter.next_reference("PRJ", width=5)
        if not self.slug:
            base = slugify(self.name)
            candidate = base
            suffix = 2
            while Project.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                candidate = f"{base}-{suffix}"
                suffix += 1
            self.slug = candidate
        super().save(*args, **kwargs)

    # -- Indicateurs ------------------------------------------------------
    @model_property
    def display_location(self) -> str:
        if self.location_text:
            return self.location_text
        return self.location.label if self.location_id else ""

    @model_property
    def is_active(self) -> bool:
        return self.status in {
            ProjectStatus.PLANNING,
            ProjectStatus.IN_PROGRESS,
            ProjectStatus.HANDOVER,
            ProjectStatus.ON_HOLD,
        }

    @model_property
    def budget_remaining_xaf(self) -> Decimal:
        return (self.budget_total_xaf or Decimal("0")) - (self.budget_spent_xaf or Decimal("0"))

    @model_property
    def budget_used_percent(self) -> float:
        from common.utils import percent

        return percent(self.budget_spent_xaf, self.budget_total_xaf)

    @model_property
    def is_over_budget(self) -> bool:
        return bool(self.budget_total_xaf and self.budget_spent_xaf > self.budget_total_xaf)

    @model_property
    def schedule_variance_days(self) -> int | None:
        """Écart entre la date prévue et la projection réelle (négatif = retard)."""
        if not self.planned_end:
            return None
        reference = self.actual_end or timezone.localdate()
        return (self.planned_end - reference).days

    @model_property
    def is_late(self) -> bool:
        if self.status in {ProjectStatus.COMPLETED, ProjectStatus.CANCELLED}:
            return False
        if not self.planned_end:
            return False
        return timezone.localdate() > self.planned_end

    @model_property
    def cover_url(self) -> str:
        return self.cover.medium_url if self.cover_id else ""

    def recalculate_progress(self, *, save: bool = True) -> Decimal:
        """Avancement physique = moyenne des phases pondérées par leur poids.

        Si aucune phase n'est définie, on conserve la valeur saisie manuellement
        (utile pour un chantier repris en cours de route, sans historique).
        """
        from django.db.models import Case, DecimalField, F, Sum, When

        aggregates = self.phases.aggregate(
            weighted=Sum(
                Case(
                    When(weight_percent__isnull=False, then=F("progress_percent") * F("weight_percent") / 100),
                    default=0,
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                )
            ),
            total_weight=Sum("weight_percent"),
        )
        total_weight = aggregates["total_weight"] or 0
        if not total_weight:
            return self.physical_progress
        progress = (aggregates["weighted"] or Decimal("0")) / Decimal(total_weight) * 100
        progress = max(Decimal("0"), min(Decimal("100"), progress.quantize(Decimal("0.01"))))
        if save and progress != self.physical_progress:
            Project.objects.filter(pk=self.pk).update(
                physical_progress=progress, updated_at=timezone.now()
            )
            self.physical_progress = progress
        return progress

    def recalculate_finance(self, *, save: bool = True) -> Decimal:
        """Dépenses engagées = somme des transactions rattachées au projet."""
        from django.db.models import Sum

        from apps.payments.models import PaymentStatus, PaymentTransaction

        total = (
            PaymentTransaction.objects.filter(
                payment__project=self.pk, status__in=[PaymentStatus.SUCCEEDED, PaymentStatus.PROCESSING]
            ).aggregate(total=Sum("payment__amount_xaf"))["total"]
            or Decimal("0")
        )
        spent = Decimal(self.budget_spent_xaf or 0)
        if save and total != spent:
            Project.objects.filter(pk=self.pk).update(budget_spent_xaf=total, updated_at=timezone.now())
            self.budget_spent_xaf = total
        return total

    def refresh_health(self, *, save: bool = True) -> str:
        """Détermine automatiquement un niveau de vigilance commercialement utile."""
        if self.status == ProjectStatus.COMPLETED:
            health = HealthStatus.COMPLETED
        elif self.is_late or self.is_over_budget:
            health = HealthStatus.AT_RISK
        elif self.budget_used_percent - float(self.physical_progress) > 15:
            # On a consommé beaucoup plus de budget que d'avancement réel.
            health = HealthStatus.WATCH
        else:
            health = HealthStatus.ON_TRACK
        if save and health != self.health:
            Project.objects.filter(pk=self.pk).update(health=health, updated_at=timezone.now())
            self.health = health
        return health

    def snapshot_metrics(self) -> dict:
        """Photo des indicateurs, utilisée par les rapports et l'historique."""
        from django.db.models import Count, Q, Sum

        from apps.construction.models import PhaseStatus
        from apps.evidences.models import EvidenceStatus

        stats = self.phases.aggregate(
            total=Count("id"),
            done=Count("id", filter=Q(status=PhaseStatus.DONE)),
            blocked=Count("id", filter=Q(status=PhaseStatus.BLOCKED)),
        )
        tasks = self.tasks.aggregate(
            total=Count("id"),
            done=Count("id", filter=Q(status="DONE")),
            overdue=Count("id", filter=Q(status__in=["TODO", "IN_PROGRESS"], due_date__lt=timezone.localdate())),
        )
        evidences = self.evidences.aggregate(
            total=Count("id"),
            pending=Count("id", filter=Q(status=EvidenceStatus.PENDING)),
            validated=Count("id", filter=Q(status=EvidenceStatus.VALIDATED)),
        )
        budget_lines = self.budget_lines.aggregate(
            planned=Sum("planned_xaf"), committed=Sum("committed_xaf"), spent=Sum("spent_xaf")
        )
        return {
            "physical_progress": float(self.physical_progress),
            "budget_used_percent": self.budget_used_percent,
            "budget_total_xaf": float(self.budget_total_xaf or 0),
            "budget_spent_xaf": float(self.budget_spent_xaf or 0),
            "phases": stats,
            "tasks": tasks,
            "evidences": evidences,
            "budget_lines": {key: float(value or 0) for key, value in budget_lines.items()},
            "is_late": self.is_late,
            "days_to_deadline": (
                (self.planned_end - timezone.localdate()).days if self.planned_end else None
            ),
        }

    def log_update(self, *, author, message: str, update_type: str = "NOTE", payload: dict | None = None,
                   visibility: str = "CUSTOMER") -> "ProjectUpdate":
        return ProjectUpdate.objects.create(
            project=self, author=author, message=message, update_type=update_type,
            payload=payload or {}, visibility=visibility,
        )


class ProjectMember(models.Model):
    """Équipe projet : qui peut voir et agir sur le chantier."""

    class MemberRole(models.TextChoices):
        MANAGER = "MANAGER", "Chargé de suivi KEMTA"
        SUPERVISOR = "SUPERVISOR", "Superviseur technique"
        FIELD = "FIELD", "Technicien terrain"
        FINANCE = "FINANCE", "Contrôleur financier"
        CLIENT_PROXY = "CLIENT_PROXY", "Représentant du client"
        OBSERVER = "OBSERVER", "Observateur"

    project = models.ForeignKey(
        Project, verbose_name="projet", on_delete=models.CASCADE, related_name="members"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="utilisateur", on_delete=models.CASCADE,
        related_name="project_memberships",
    )
    role = models.CharField("rôle", max_length=16, choices=MemberRole.choices, default=MemberRole.FIELD)
    can_capture_evidence = models.BooleanField("peut publier des preuves", default=True)
    can_validate_evidence = models.BooleanField("peut valider des preuves", default=False)
    can_view_finance = models.BooleanField("accès aux finances", default=False)
    can_manage_schedule = models.BooleanField("gère le planning", default=False)
    receives_notifications = models.BooleanField("reçoit les notifications", default=True)
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="ajouté par", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+",
    )
    joined_at = models.DateTimeField("a rejoint le", auto_now_add=True)
    removed_at = models.DateTimeField("retiré le", null=True, blank=True)

    class Meta:
        verbose_name = "membre de projet"
        verbose_name_plural = "membres de projet"
        constraints = [
            models.UniqueConstraint(fields=("project", "user"), name="uniq_project_member"),
        ]
        indexes = [
            models.Index(fields=("user", "removed_at")),
            models.Index(fields=("project", "role")),
        ]

    def __str__(self) -> str:
        return f"{self.user.full_name} — {self.project.reference} ({self.get_role_display()})"

    @property
    def is_active(self) -> bool:
        return self.removed_at is None


class BudgetLine(models.Model):
    """Ligne budgétaire d'un projet (matériaux, main-d'œuvre, transport…)."""

    class Category(models.TextChoices):
        MATERIAUX = "MATERIAUX", "Matériaux"
        MAIN_OEUVRE = "MAIN_OEUVRE", "Main-d'œuvre"
        TRANSPORT = "TRANSPORT", "Transport et logistique"
        LOCATION = "LOCATION", "Location de matériel"
        ETUDES = "ETUDES", "Études et honoraires"
        ADMINISTRATIF = "ADMINISTRATIF", "Frais administratifs"
        DIVERS = "DIVERS", "Divers"

    project = models.ForeignKey(
        Project, verbose_name="projet", on_delete=models.CASCADE, related_name="budget_lines"
    )
    phase = models.ForeignKey(
        "construction.Phase", verbose_name="phase", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="budget_lines",
    )
    category = models.CharField("catégorie", max_length=16, choices=Category.choices, default=Category.MATERIAUX)
    label = models.CharField("libellé", max_length=180)
    planned_xaf = models.DecimalField(
        "prévu (FCFA)", max_digits=14, decimal_places=2, default=0,
        validators=[MinValueValidator(0)],
    )
    committed_xaf = models.DecimalField(
        "commandé (FCFA)", max_digits=14, decimal_places=2, default=0,
        validators=[MinValueValidator(0)],
    )
    spent_xaf = models.DecimalField(
        "payé (FCFA)", max_digits=14, decimal_places=2, default=0,
        validators=[MinValueValidator(0)],
    )
    supplier = models.CharField("fournisseur", max_length=180, blank=True)
    notes = models.CharField("notes", max_length=255, blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "ligne budgétaire"
        verbose_name_plural = "lignes budgétaires"
        ordering = ("category", "label")
        indexes = [models.Index(fields=("project", "category"))]

    def __str__(self) -> str:
        return f"{self.label} — {self.project.reference}"

    @property
    def variance_xaf(self) -> Decimal:
        return (self.planned_xaf or Decimal("0")) - (self.spent_xaf or Decimal("0"))

    @property
    def is_overspent(self) -> bool:
        return bool(self.planned_xaf and self.spent_xaf > self.planned_xaf)


class ProjectUpdate(models.Model):
    """Mise à jour publiée dans le fil du projet (journal du chantier)."""

    class UpdateType(models.TextChoices):
        NOTE = "NOTE", "Note de suivi"
        PROGRESS = "PROGRESS", "Avancement"
        PHASE = "PHASE", "Étape du chantier"
        TASK = "TASK", "Tâche"
        EVIDENCE = "EVIDENCE", "Preuve terrain"
        REPORT = "REPORT", "Rapport"
        FINANCE = "FINANCE", "Finance"
        INCIDENT = "INCIDENT", "Incident / alerte"
        MILESTONE = "MILESTONE", "Jalon majeur"
        DOCUMENT = "DOCUMENT", "Document partagé"
        COMMENT = "COMMENT", "Commentaire client"

    project = models.ForeignKey(
        Project, verbose_name="projet", on_delete=models.CASCADE, related_name="updates"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="auteur", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="project_updates",
    )
    update_type = models.CharField("type", max_length=12, choices=UpdateType.choices, default=UpdateType.NOTE)
    message = models.TextField("message")
    payload = models.JSONField("données", default=dict, blank=True)
    visibility = models.CharField(
        "visibilité", max_length=10,
        choices=[("CUSTOMER", "Client et équipe"), ("TEAM", "Équipe KEMTA"), ("PUBLIC", "Public")],
        default="CUSTOMER",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "mise à jour de projet"
        verbose_name_plural = "mises à jour de projet"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("project", "-created_at")),
            models.Index(fields=("update_type",)),
        ]

    def __str__(self) -> str:
        return f"{self.project.reference} — {self.get_update_type_display()}"


class ProjectDocument(models.Model):
    """Document partagé du projet (plan, contrat, facture, procès-verbal)."""

    class DocumentKind(models.TextChoices):
        CONTRACT = "CONTRACT", "Contrat"
        PLAN = "PLAN", "Plan / architecture"
        QUOTE = "QUOTE", "Devis"
        INVOICE = "INVOICE", "Facture"
        PERMIT = "PERMIT", "Autorisation / titre foncier"
        REPORT = "REPORT", "Rapport"
        HANDOVER = "HANDOVER", "Procès-verbal de réception"
        OTHER = "OTHER", "Autre"

    project = models.ForeignKey(
        Project, verbose_name="projet", on_delete=models.CASCADE, related_name="documents"
    )
    kind = models.CharField("type", max_length=12, choices=DocumentKind.choices, default=DocumentKind.OTHER)
    title = models.CharField("intitulé", max_length=180)
    asset = models.ForeignKey(
        "common.Asset", verbose_name="fichier", on_delete=models.PROTECT, related_name="project_documents"
    )
    visible_to_customer = models.BooleanField("visible par le client", default=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="déposé par", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "document de projet"
        verbose_name_plural = "documents de projet"
        ordering = ("kind", "-created_at")
        indexes = [models.Index(fields=("project", "kind"))]

    def __str__(self) -> str:
        return f"{self.title} — {self.project.reference}"


class Task(models.Model):
    """Tâche opérationnelle rattachée à un projet (et éventuellement une phase)."""

    class Status(models.TextChoices):
        TODO = "TODO", "À faire"
        IN_PROGRESS = "IN_PROGRESS", "En cours"
        BLOCKED = "BLOCKED", "Bloquée"
        DONE = "DONE", "Terminée"
        CANCELLED = "CANCELLED", "Annulée"

    class Priority(models.TextChoices):
        LOW = "LOW", "Basse"
        NORMAL = "NORMAL", "Normale"
        HIGH = "HIGH", "Haute"
        URGENT = "URGENT", "Urgente"

    project = models.ForeignKey(
        Project, verbose_name="projet", on_delete=models.CASCADE, related_name="tasks"
    )
    phase = models.ForeignKey(
        "construction.Phase", verbose_name="phase", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="tasks",
    )
    title = models.CharField("intitulé", max_length=200)
    description = models.TextField("détail", blank=True)
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="responsable", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="tasks",
    )
    status = models.CharField("statut", max_length=12, choices=Status.choices, default=Status.TODO, db_index=True)
    priority = models.CharField("priorité", max_length=8, choices=Priority.choices, default=Priority.NORMAL)
    due_date = models.DateField("échéance", null=True, blank=True, db_index=True)
    started_at = models.DateTimeField("démarrée le", null=True, blank=True)
    completed_at = models.DateTimeField("terminée le", null=True, blank=True)
    requires_evidence = models.BooleanField("preuve photo requise", default=False)
    progress_percent = models.PositiveSmallIntegerField(
        "avancement (%)", default=0, validators=[MaxValueValidator(100)]
    )
    order = models.PositiveIntegerField("ordre", default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="créée par", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="created_tasks",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "tâche"
        verbose_name_plural = "tâches"
        ordering = ("order", "due_date", "-created_at")
        indexes = [
            models.Index(fields=("project", "status")),
            models.Index(fields=("assignee", "status")),
            models.Index(fields=("due_date", "status")),
        ]

    def __str__(self) -> str:
        return self.title

    @property
    def is_overdue(self) -> bool:
        return bool(
            self.due_date
            and self.status in {self.Status.TODO, self.Status.IN_PROGRESS, self.Status.BLOCKED}
            and self.due_date < timezone.localdate()
        )

    @property
    def is_done(self) -> bool:
        return self.status == self.Status.DONE

    @transaction.atomic
    def mark_done(self, *, by=None) -> None:
        self.status = self.Status.DONE
        self.progress_percent = 100
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "progress_percent", "completed_at", "updated_at"])
        if self.phase_id:
            self.phase.recalculate_progress()
