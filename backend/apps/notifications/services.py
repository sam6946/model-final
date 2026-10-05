"""Création et distribution des notifications.

Séquence retenue :

1. la notification est **toujours** écrite en base (canal in-app) : le client
   retrouve l'information même si l'opérateur SMS est en panne ;
2. les canaux externes (SMS, e-mail, WhatsApp) sont envoyés par Celery :
   la requête HTTP n'attend jamais un opérateur tiers ;
3. la déduplication (``dedupe_key``) empêche d'envoyer deux fois la même alerte ;
4. les préférences utilisateur sont respectées canal par canal.
"""
from __future__ import annotations

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.notifications.models import (
    Notification,
    NotificationPreference,
    NotificationStatus,
    NotificationTemplate,
)
from common.constants import NotificationChannel, NotificationType

logger = logging.getLogger("kemta.notifications")


def preferences_for(user) -> NotificationPreference:
    preference, _created = NotificationPreference.objects.get_or_create(user=user)
    return preference


def render_template(*, notification_type: str, channel: str, context: dict, fallback: str) -> str:
    """Applique un gabarit administrable ; retombe sur le texte fourni sinon."""
    template = NotificationTemplate.objects.filter(
        notification_type=notification_type, channel=channel, is_active=True
    ).first()
    if template is None:
        return fallback
    try:
        return template.body.format(**context)
    except (KeyError, IndexError, ValueError):
        logger.warning("notification_template_render_failed", extra={"type": notification_type})
        return fallback


@transaction.atomic
def notify(
    *,
    recipient,
    notification_type: str,
    title: str,
    body: str,
    channel: str = NotificationChannel.IN_APP,
    action_url: str = "",
    action_label: str = "",
    entity_type: str = "",
    entity_id: int | None = None,
    project=None,
    payload: dict | None = None,
    dedupe_key: str = "",
    scheduled_for=None,
    also_sms: bool = False,
) -> Notification | None:
    """Crée une notification (in-app) et programme les canaux additionnels.

    Renvoie ``None`` si la déduplication indique que l'alerte a déjà été émise.
    """
    if dedupe_key:
        exists = Notification.objects.filter(recipient=recipient, dedupe_key=dedupe_key).exists()
        if exists:
            return None

    preference = preferences_for(recipient)
    context = {
        "prenom": getattr(recipient, "first_name", "") or "cher client",
        "nom": getattr(recipient, "last_name", ""),
        "reference": (payload or {}).get("reference", ""),
        "projet": (payload or {}).get("project_name", ""),
        "montant": (payload or {}).get("amount_label", ""),
        "lien": action_url,
    }

    notification = Notification(
        recipient=recipient,
        notification_type=notification_type,
        channel=NotificationChannel.IN_APP,
        title=title[:180],
        body=body,
        action_url=action_url,
        action_label=action_label[:60],
        entity_type=entity_type[:40],
        entity_id=entity_id,
        project=project,
        payload=payload or {},
        dedupe_key=dedupe_key,
        scheduled_for=scheduled_for or timezone.now(),
        status=NotificationStatus.PENDING,
    )
    try:
        notification.save()
    except IntegrityError:
        # Contrainte d'unicité = alerte déjà partie : on ne double pas.
        return None

    # Préférences : un utilisateur qui a coupé les notifications in-app ne
    # reçoit pas de canal externe non plus (sauf sécurité).
    wants_in_app = preference.allows(channel=NotificationChannel.IN_APP, notification_type=notification_type)
    if not wants_in_app and notification_type != NotificationType.SECURITY:
        Notification.objects.filter(pk=notification.pk).update(status=NotificationStatus.FAILED,
                                                               failed_reason="Désactivé par l'utilisateur")
        return notification

    channels: list[str] = [NotificationChannel.IN_APP]
    if also_sms and preference.allows(channel=NotificationChannel.SMS, notification_type=notification_type):
        channels.append(NotificationChannel.SMS)
    if (
        getattr(recipient, "email", None)
        and preference.allows(channel=NotificationChannel.EMAIL, notification_type=notification_type)
    ):
        channels.append(NotificationChannel.EMAIL)

    from apps.notifications.tasks import deliver_notification

    for target_channel in channels:
        if settings.CELERY_TASK_ALWAYS_EAGER:
            deliver_notification.apply(kwargs={"notification_id": notification.pk, "channel": target_channel},
                                       throw=False)
        else:
            transaction.on_commit(
                lambda c=target_channel: deliver_notification.delay(
                    notification_id=notification.pk, channel=c
                )
            )
    return notification


def notify_many(*, recipients, **kwargs) -> int:
    created = 0
    for recipient in recipients:
        if notify(recipient=recipient, **kwargs) is not None:
            created += 1
    return created


def send_transactional_email(*, to: str, subject: str, body: str, dedupe_key: str = "") -> bool:
    """E-mail transactionnel (reçu, facture, information importante).

    Volontairement découplé des notifications in-app : utilisé quand le
    destinataire n'a pas encore de compte (visiteur ayant laissé un e-mail).
    """
    if not to:
        return False
    if dedupe_key:
        from django.core.cache import cache

        key = f"kemta:email:{dedupe_key}"
        if cache.get(key):
            return False
        cache.set(key, 1, 60 * 60 * 24)

    from apps.notifications.tasks import send_email_task

    if settings.CELERY_TASK_ALWAYS_EAGER:
        return send_email_task.apply(kwargs={"to": to, "subject": subject, "body": body}, throw=False).get() or False
    send_email_task.delay(to=to, subject=subject, body=body)
    return True


def deliver_now(*, notification: Notification, channel: str) -> bool:
    """Livre une notification sur un canal donné (appelé par Celery)."""
    preference = preferences_for(notification.recipient)
    if channel == NotificationChannel.IN_APP:
        notification.mark_sent()
        return True

    if channel == NotificationChannel.SMS:
        if not preference.allows(channel=NotificationChannel.SMS, notification_type=notification.notification_type):
            return False
        from common.services.sms import SmsError, send_sms

        message = render_template(
            notification_type=notification.notification_type,
            channel=NotificationChannel.SMS,
            context={
                "prenom": notification.recipient.first_name or "",
                "reference": (notification.payload or {}).get("reference", ""),
                "projet": (notification.payload or {}).get("project_name", ""),
                "montant": (notification.payload or {}).get("amount_label", ""),
                "lien": notification.action_url,
            },
            fallback=f"KEMTA : {notification.title}. {notification.body[:120]}",
        )
        try:
            result = send_sms(phone=notification.recipient.phone, message=message[:320])
        except SmsError:
            notification.mark_failed(reason="Opérateur SMS indisponible")
            raise
        if result.delivered:
            notification.mark_sent(reference=result.reference)
            return True
        notification.mark_failed(reason=result.detail or "Envoi SMS refusé")
        return False

    if channel == NotificationChannel.EMAIL:
        if not getattr(notification.recipient, "email", None):
            return False
        send_mail(
            subject=notification.title,
            message=f"{notification.body}\n\n{settings.KEMTA_BRAND_NAME}\n{settings.KEMTA_SUPPORT_EMAIL}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[notification.recipient.email],
            fail_silently=True,
        )
        notification.mark_sent()
        return True

    if channel == NotificationChannel.WHATSAPP:
        if not settings.WHATSAPP_ENABLED:
            logger.info("whatsapp_disabled", extra={"notification_id": notification.pk})
            return False
        logger.info("whatsapp_pending_integration", extra={"notification_id": notification.pk})
        return False

    return False


def mark_all_read(*, user) -> int:
    return Notification.objects.filter(recipient=user, read_at__isnull=True).update(
        read_at=timezone.now(), status=NotificationStatus.READ
    )


def unread_count(*, user) -> int:
    return Notification.objects.filter(recipient=user, read_at__isnull=True).count()
