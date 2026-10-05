"""Journal d'activité : la trace « qui a fait quoi » sur la plateforme.

Il alimente :

- le fil d'activité du dashboard client (« ce qui s'est passé sur mon projet ») ;
- le contrôle interne KEMTA (audit opérationnel) ;
- l'écran « Activité » du back-office.

Il est volontairement dénormalisé (verbe + libellé lisible) pour que l'API
puisse renvoyer un fil directement affichable sans jointure côté frontend.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models


class ActivityVerb(models.TextChoices):
    REQUEST_RECEIVED = "REQUEST_RECEIVED", "Demande reçue"
    REQUEST_STATUS_CHANGED = "REQUEST_STATUS_CHANGED", "Statut de demande modifié"
    REQUEST_ASSIGNED = "REQUEST_ASSIGNED", "Demande assignée"
    PROJECT_CREATED = "PROJECT_CREATED", "Projet créé"
    PROJECT_UPDATED = "PROJECT_UPDATED", "Projet mis à jour"
    PROJECT_STATUS_CHANGED = "PROJECT_STATUS_CHANGED", "Statut du projet modifié"
    PHASE_UPDATED = "PHASE_UPDATED", "Étape mise à jour"
    TASK_CREATED = "TASK_CREATED", "Tâche créée"
    TASK_COMPLETED = "TASK_COMPLETED", "Tâche terminée"
    EVIDENCE_UPLOADED = "EVIDENCE_UPLOADED", "Preuve déposée"
    EVIDENCE_VALIDATED = "EVIDENCE_VALIDATED", "Preuve validée"
    EVIDENCE_REJECTED = "EVIDENCE_REJECTED", "Preuve refusée"
    REPORT_CREATED = "REPORT_CREATED", "Rapport rédigé"
    REPORT_VALIDATED = "REPORT_VALIDATED", "Rapport validé"
    DOCUMENT_UPLOADED = "DOCUMENT_UPLOADED", "Document déposé"
    PAYMENT_INITIATED = "PAYMENT_INITIATED", "Paiement initié"
    PAYMENT_SUCCEEDED = "PAYMENT_SUCCEEDED", "Paiement encaissé"
    PAYMENT_FAILED = "PAYMENT_FAILED", "Paiement échoué"
    INVOICE_CREATED = "INVOICE_CREATED", "Facture émise"
    SUBSCRIPTION_CHANGED = "SUBSCRIPTION_CHANGED", "Abonnement modifié"
    COMPANY_CREATED = "COMPANY_CREATED", "Entreprise créée"
    COMPANY_VERIFIED = "COMPANY_VERIFIED", "Entreprise vérifiée"
    COMPANY_REJECTED = "COMPANY_REJECTED", "Dossier entreprise à compléter"
    CATALOG_PUBLISHED = "CATALOG_PUBLISHED", "Réalisation publiée"
    CATALOG_UPDATED = "CATALOG_UPDATED", "Réalisation mise à jour"
    OPPORTUNITY_CREATED = "OPPORTUNITY_CREATED", "Opportunité publiée"
    APPLICATION_SUBMITTED = "APPLICATION_SUBMITTED", "Candidature déposée"
    APPLICATION_STATUS_CHANGED = "APPLICATION_STATUS_CHANGED", "Statut de candidature modifié"
    PROPERTY_CREATED = "PROPERTY_CREATED", "Propriété enregistrée"
    VISIT_SCHEDULED = "VISIT_SCHEDULED", "Visite planifiée"
    VISIT_COMPLETED = "VISIT_COMPLETED", "Visite réalisée"
    ISSUE_REPORTED = "ISSUE_REPORTED", "Problème signalé"
    MEMBER_ADDED = "MEMBER_ADDED", "Membre ajouté"
    LOGIN = "LOGIN", "Connexion"
    SETTINGS_CHANGED = "SETTINGS_CHANGED", "Paramètres modifiés"


class ActivityLog(models.Model):
    """Événement d'activité horodaté, rattaché à ses objets métier."""

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="auteur", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="activities",
    )
    verb = models.CharField("action", max_length=32, choices=ActivityVerb.choices, db_index=True)
    message = models.CharField("libellé affichable", max_length=255)

    project = models.ForeignKey(
        "projects.Project", verbose_name="projet", null=True, blank=True,
        on_delete=models.CASCADE, related_name="activities",
    )
    company = models.ForeignKey(
        "companies.Company", verbose_name="entreprise", null=True, blank=True,
        on_delete=models.CASCADE, related_name="activities",
    )
    property = models.ForeignKey(
        "properties.Property", verbose_name="propriété", null=True, blank=True,
        on_delete=models.CASCADE, related_name="activities",
    )

    entity_type = models.CharField("type d'objet", max_length=40, blank=True)
    entity_id = models.PositiveBigIntegerField("identifiant d'objet", null=True, blank=True)
    url = models.CharField("lien", max_length=255, blank=True)
    payload = models.JSONField("données", default=dict, blank=True)

    visibility = models.CharField(
        "visibilité", max_length=10,
        choices=[("CUSTOMER", "Client"), ("TEAM", "Équipe KEMTA"), ("PUBLIC", "Public")],
        default="TEAM",
    )
    is_important = models.BooleanField("événement marquant", default=False)
    ip_address = models.GenericIPAddressField("adresse IP", null=True, blank=True)
    user_agent = models.CharField("agent utilisateur", max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "activité"
        verbose_name_plural = "activités"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("project", "-created_at")),
            models.Index(fields=("company", "-created_at")),
            models.Index(fields=("actor", "-created_at")),
            models.Index(fields=("verb", "-created_at")),
            models.Index(fields=("visibility", "-created_at")),
        ]

    def __str__(self) -> str:
        return f"{self.get_verb_display()} — {self.message[:60]}"

    def save(self, *args, **kwargs) -> None:
        if not self.message:
            self.message = self.get_verb_display()
        super().save(*args, **kwargs)


class AuditLog(models.Model):
    """Audit de sécurité : accès sensibles et actions d'administration."""

    class Action(models.TextChoices):
        VIEW = "VIEW", "Consultation"
        CREATE = "CREATE", "Création"
        UPDATE = "UPDATE", "Modification"
        DELETE = "DELETE", "Suppression"
        EXPORT = "EXPORT", "Export de données"
        LOGIN = "LOGIN", "Connexion"
        LOGOUT = "LOGOUT", "Déconnexion"
        PERMISSION_DENIED = "PERMISSION_DENIED", "Accès refusé"
        CONFIG_CHANGE = "CONFIG_CHANGE", "Modification de configuration"
        PAYMENT = "PAYMENT", "Opération de paiement"
        VERIFY = "VERIFY", "Validation"
        IMPERSONATE = "IMPERSONATE", "Accès délégué"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="utilisateur", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="audit_logs",
    )
    action = models.CharField("action", max_length=20, choices=Action.choices, db_index=True)
    entity_type = models.CharField("type d'objet", max_length=60, blank=True)
    entity_id = models.CharField("identifiant d'objet", max_length=60, blank=True)
    description = models.CharField("description", max_length=255, blank=True)
    changes = models.JSONField("modifications", default=dict, blank=True)
    path = models.CharField("chemin", max_length=255, blank=True)
    method = models.CharField("méthode HTTP", max_length=10, blank=True)
    status_code = models.PositiveSmallIntegerField("code de réponse", null=True, blank=True)
    ip_address = models.GenericIPAddressField("adresse IP", null=True, blank=True)
    user_agent = models.CharField("agent utilisateur", max_length=255, blank=True)
    trace_id = models.CharField("identifiant de trace", max_length=40, blank=True, db_index=True)
    duration_ms = models.PositiveIntegerField("durée (ms)", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "journal d'audit"
        verbose_name_plural = "journaux d'audit"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("action", "-created_at")),
            models.Index(fields=("user", "-created_at")),
            models.Index(fields=("entity_type", "entity_id")),
        ]

    def __str__(self) -> str:
        return f"{self.get_action_display()} — {self.entity_type}:{self.entity_id}"
