"""Serializers du fil d'activité et de l'audit."""
from __future__ import annotations

from rest_framework import serializers

from apps.activities.models import ActivityLog, AuditLog


class ActivityLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source="actor.full_name", read_only=True, default="Système")
    actor_initials = serializers.CharField(source="actor.initials", read_only=True, default="KE")
    verb_label = serializers.CharField(source="get_verb_display", read_only=True)
    project_reference = serializers.CharField(source="project.reference", read_only=True, default="")
    age_label = serializers.SerializerMethodField()

    class Meta:
        model = ActivityLog
        fields = (
            "id", "verb", "verb_label", "message", "actor_name", "actor_initials",
            "project_reference", "entity_type", "entity_id", "url", "payload",
            "visibility", "is_important", "created_at", "age_label",
        )

    def get_age_label(self, obj: ActivityLog) -> str:
        from django.utils.timesince import timesince

        return f"il y a {timesince(obj.created_at).split(',')[0]}"


class AuditLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.full_name", read_only=True, default="")
    action_label = serializers.CharField(source="get_action_display", read_only=True)

    class Meta:
        model = AuditLog
        fields = (
            "id", "user", "user_name", "action", "action_label", "entity_type", "entity_id",
            "description", "changes", "path", "method", "status_code", "ip_address",
            "trace_id", "duration_ms", "created_at",
        )
