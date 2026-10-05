"""Notifications centralisées et préférences par utilisateur.

Une notification est créée en base (canal « in-app » toujours disponible), puis
les canaux externes (SMS, e-mail, WhatsApp) sont traités par Celery. Cette
séparation garantit qu'un incident d'opérateur SMS ne fait jamais perdre
l'information côté application, et qu'un utilisateur qui rouvre son dossier
retrouve tout l'historique.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone

from common.constants import Level, NotificationChannel, NotificationStatus, NotificationType


class Notification(models.Model):
    """Message adressé à un utilisateur, tous canaux confondus."""

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="destinataire", on_delete=models.CASCADE,
        related_name="notifications",
    )
    notification_type = models.CharField(
        "type", max_length=20, choices=NotificationType.choices, default=NotificationType.SYSTEM,
        db_index=True,
    )
    level = models.CharField("niveau", max_length=8, choices=Level.choices, default=Level.INFO)
    channel = models.CharField(
        "canal", max_length=10, choices=NotificationChannel.choices, default=NotificationChannel.IN_APP
    )
    status = models.CharField(
        "statut", max_length=8, choices=NotificationStatus.choices, default=NotificationStatus.PENDING,
        db_index=True,
    )

    title = models.CharField("titre", max_length=180)
    body = models.TextField("message")
    action_url = models.CharField("lien d'action", max_length=255, blank=True)
    action_label = models.CharField("libellé du bouton", max_length=60, blank=True)

    # Rattachement souple : évite une table de jointure par type d'objet.
    entity_type = models.CharField("type d'objet lié", max_length=40, blank=True)
    entity_id = models.PositiveBigIntegerField("identifiant d'objet", null=True, blank=True)
    project = models.ForeignKey(
        "projects.Project", verbose_name="projet", null=True, blank=True,
        on_delete=models.CASCADE, related_name="notifications",
    )
    payload = models.JSONField("données", default=dict, blank=True)

    dedupe_key = models.CharField(
        "clé de déduplication", max_length=120, blank=True, db_index=True,
        help_text="Empêche d'envoyer deux fois la même alerte (ex. « échéance J-1 »).",
    )
    scheduled_for = models.DateTimeField("programmée pour", null=True, blank=True, db_index=True)
    sent_at = models.DateTimeField("envoyée le", null=True, blank=True)
    read_at = models.DateTimeField("lue le", null=True, blank=True)
    failed_reason = models.CharField("motif d'échec", max_length=255, blank=True)
    attempts = models.PositiveSmallIntegerField("tentatives", default=0)
    provider_reference = models.CharField("référence opérateur", max_length=120, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="émise par", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="emitted_notifications",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "notification"
        verbose_name_plural = "notifications"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("recipient", "read_at", "-created_at")),
            models.Index(fields=("recipient", "notification_type")),
            models.Index(fields=("status", "scheduled_for")),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=("recipient", "dedupe_key"),
                condition=models.Q(dedupe_key__gt=""),
                name="uniq_notification_dedupe",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.notification_type} → {self.recipient_id}"

    @property
    def is_read(self) -> bool:
        return self.read_at is not None

    @property
    def is_sent(self) -> bool:
        return self.status in {NotificationStatus.SENT, NotificationStatus.READ}

    def mark_read(self) -> None:
        Notification.objects.filter(pk=self.pk).update(
            read_at=timezone.now(), status=NotificationStatus.READ
        )

    def mark_sent(self, *, reference: str = "") -> None:
        Notification.objects.filter(pk=self.pk).update(
            status=NotificationStatus.SENT, sent_at=timezone.now(), provider_reference=reference[:120]
        )

    def mark_failed(self, *, reason: str) -> None:
        Notification.objects.filter(pk=self.pk).update(
            status=NotificationStatus.FAILED, failed_reason=reason[:255],
            attempts=models.F("attempts") + 1,
        )


class NotificationPreference(models.Model):
    """Préférences de contact : l'utilisateur choisit, KEMTA respecte."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, verbose_name="utilisateur", on_delete=models.CASCADE,
        related_name="notification_preferences",
    )
    in_app = models.BooleanField("notifications dans l'application", default=True)
    sms = models.BooleanField("notifications par SMS", default=True)
    email = models.BooleanField("notifications par e-mail", default=True)
    whatsapp = models.BooleanField("notifications WhatsApp", default=False)

    project_updates = models.BooleanField("avancement des chantiers", default=True)
    evidence_validated = models.BooleanField("validation des preuves terrain", default=True)
    task_reminders = models.BooleanField("rappels de tâches", default=True)
    payment_events = models.BooleanField("paiements et factures", default=True)
    subscription_events = models.BooleanField("abonnements", default=True)
    opportunity_alerts = models.BooleanField("nouvelles opportunités BTP", default=True)
    marketing = models.BooleanField("informations et offres KEMTA", default=False)

    quiet_hours_start = models.TimeField("début des heures calmes", null=True, blank=True)
    quiet_hours_end = models.TimeField("fin des heures calmes", null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "préférences de notification"
        verbose_name_plural = "préférences de notification"

    def __str__(self) -> str:
        return f"Préférences de {self.user_id}"

    def allows(self, *, channel: str, notification_type: str) -> bool:
        """Détermine si l'utilisateur accepte ce canal pour ce type."""
        channel_map = {
            NotificationChannel.IN_APP: self.in_app,
            NotificationChannel.SMS: self.sms,
            NotificationChannel.EMAIL: self.email,
            NotificationChannel.WHATSAPP: self.whatsapp,
        }
        if not channel_map.get(channel, True):
            return False
        type_map = {
            NotificationType.PROJECT: self.project_updates,
            NotificationType.EVIDENCE: self.evidence_validated,
            NotificationType.TASK: self.task_reminders,
            NotificationType.PAYMENT: self.payment_events,
            NotificationType.SUBSCRIPTION: self.subscription_events,
            NotificationType.OPPORTUNITY: self.opportunity_alerts,
        }
        # Les alertes de sécurité ne sont jamais désactivables.
        if notification_type == NotificationType.SECURITY:
            return True
        return type_map.get(notification_type, True)


class NotificationTemplate(models.Model):
    """Gabarit de message par type et canal (modifiable sans redéploiement)."""

    notification_type = models.CharField("type", max_length=20, choices=NotificationType.choices)
    channel = models.CharField("canal", max_length=10, choices=NotificationChannel.choices)
    subject = models.CharField("sujet", max_length=180, blank=True)
    body = models.TextField(
        "gabarit",
        help_text="Variables disponibles : {prenom}, {reference}, {projet}, {lien}, {montant}…",
    )
    is_active = models.BooleanField("actif", default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "gabarit de notification"
        verbose_name_plural = "gabarits de notification"
        constraints = [
            models.UniqueConstraint(
                fields=("notification_type", "channel"), name="uniq_notification_template"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.get_notification_type_display()} / {self.get_channel_display()}"
