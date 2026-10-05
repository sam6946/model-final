"""Invalidation du cache du tableau de bord à chaque écriture métier.

Le tableau de bord agrège projets, preuves, notifications et candidatures :
dès qu'une de ces données change, le cache de l'utilisateur concerné est
supprimé pour que l'écran reste exact (TanStack Query ne peut pas deviner
une donnée modifiée par un tiers).
"""
from __future__ import annotations

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.dashboard.services import invalidate_dashboard
from apps.notifications.models import Notification
from apps.projects.models import Project, ProjectMember, ProjectUpdate


def _project_users(project) -> list:
    users = [project.customer, project.manager]
    users += [
        member.user
        for member in ProjectMember.objects.filter(
            project=project, removed_at__isnull=True
        ).select_related("user")
    ]
    return users


@receiver(post_save, sender=Project, dispatch_uid="kemta.dashboard.project")
def _project_saved(sender, instance, **kwargs):
    invalidate_dashboard(*_project_users(instance))


@receiver(post_save, sender=ProjectUpdate, dispatch_uid="kemta.dashboard.project_update")
def _project_update_saved(sender, instance, **kwargs):
    invalidate_dashboard(*_project_users(instance.project))


@receiver(post_save, sender=ProjectMember, dispatch_uid="kemta.dashboard.project_member")
def _project_member_saved(sender, instance, **kwargs):
    invalidate_dashboard(instance.user, instance.project.customer, instance.project.manager)


@receiver(post_save, sender=Notification, dispatch_uid="kemta.dashboard.notification")
def _notification_saved(sender, instance, **kwargs):
    invalidate_dashboard(instance.recipient)
