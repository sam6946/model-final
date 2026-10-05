"""Tâches Celery des notifications (livraison, rappels, relances)."""
from __future__ import annotations

import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

logger = logging.getLogger("kemta.tasks.notifications")


@shared_task(
    name="apps.notifications.tasks.deliver_notification",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def deliver_notification(self, *, notification_id: int, channel: str) -> dict:
    """Livre une notification sur un canal ; retente les erreurs temporaires."""
    from apps.notifications.models import Notification
    from apps.notifications.services import deliver_now
    from common.services.sms import SmsError

    try:
        notification = Notification.objects.select_related("recipient").get(pk=notification_id)
    except Notification.DoesNotExist:
        return {"status": "missing"}

    try:
        delivered = deliver_now(notification=notification, channel=channel)
    except SmsError as exc:
        raise self.retry(exc=exc, countdown=60 * (2**self.request.retries)) from exc
    except Exception as exc:  # pragma: no cover
        logger.exception("notification_delivery_failed", extra={"notification_id": notification_id})
        notification.mark_failed(reason=str(exc))
        return {"status": "error"}

    return {"status": "sent" if delivered else "skipped", "channel": channel}


@shared_task(name="apps.notifications.tasks.send_email_task", bind=True, max_retries=2)
def send_email_task(self, *, to: str, subject: str, body: str) -> bool:
    """Envoi d'e-mail hors requête HTTP (jamais bloquant)."""
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to],
            fail_silently=False,
        )
        return True
    except Exception as exc:  # pragma: no cover
        logger.warning("email_send_failed", extra={"to": to, "error": str(exc)})
        raise self.retry(exc=exc, countdown=120) from exc


@shared_task(name="apps.notifications.tasks.dispatch_pending")
def dispatch_pending(limit: int = 200) -> int:
    """Reprend les notifications restées en attente (incident opérateur, redéploiement)."""
    from apps.notifications.models import Notification, NotificationStatus

    pending = Notification.objects.filter(
        status=NotificationStatus.PENDING, scheduled_for__lte=timezone.now()
    ).order_by("created_at")[:limit]
    count = 0
    for notification in pending:
        deliver_notification.delay(notification_id=notification.pk, channel="IN_APP")
        count += 1
    return count


@shared_task(name="apps.notifications.tasks.send_daily_digests")
def send_daily_digests() -> int:
    """Résumé quotidien aux chargés de suivi (tâches du jour, alertes)."""
    from django.contrib.auth import get_user_model
    from django.db.models import Count, Q

    from apps.maintenance.models import MaintenanceVisit
    from apps.notifications.services import notify
    from apps.projects.models import Task
    from common.constants import NotificationType

    User = get_user_model()
    today = timezone.localdate()
    sent = 0
    managers = User.objects.filter(role__in=["MANAGER", "ADMIN"], is_active=True)

    tasks_by_user = {
        row["assignee_id"]: row
        for row in Task.objects.filter(
            assignee__in=managers, status__in=["TODO", "IN_PROGRESS"]
        )
        .values("assignee_id")
        .annotate(total=Count("id"), overdue=Count("id", filter=Q(due_date__lt=today)))
    }
    visits_by_user = {
        row["technician_id"]: row
        for row in MaintenanceVisit.objects.filter(
            technician__in=managers, status__in=["SCHEDULED", "CONFIRMED"], scheduled_for__date=today
        )
        .values("technician_id")
        .annotate(total=Count("id"))
    }

    for manager in managers:
        tasks = tasks_by_user.get(manager.pk, {})
        visits = visits_by_user.get(manager.pk, {})
        if not tasks and not visits:
            continue
        parts = []
        if tasks.get("total"):
            parts.append(f"{tasks['total']} tâche(s) en cours dont {tasks.get('overdue', 0)} en retard")
        if visits.get("total"):
            parts.append(f"{visits['total']} visite(s) d'entretien programmée(s) aujourd'hui")
        notify(
            recipient=manager,
            notification_type=NotificationType.TASK,
            title="Votre journée sur KEMTA",
            body=" · ".join(parts),
            action_url="/admin",
            action_label="Ouvrir le back-office",
            dedupe_key=f"digest:{manager.pk}:{today.isoformat()}",
        )
        sent += 1
    return sent
