"""Serializers des notifications et des préférences de contact."""
from __future__ import annotations

from rest_framework import serializers

from apps.notifications.models import Notification, NotificationPreference


class NotificationSerializer(serializers.ModelSerializer):
    type_label = serializers.CharField(source="get_notification_type_display", read_only=True)
    level_label = serializers.CharField(source="get_level_display", read_only=True)
    is_read = serializers.BooleanField(read_only=True)
    age_label = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = (
            "id", "notification_type", "type_label", "level", "level_label", "title", "body",
            "action_url", "action_label", "entity_type", "entity_id", "payload",
            "read_at", "is_read", "created_at", "age_label",
        )

    def get_age_label(self, obj: Notification) -> str:
        from django.utils.timesince import timesince

        return f"il y a {timesince(obj.created_at).split(',')[0]}"


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        exclude = ("id", "user", "updated_at")


class NotificationCreateSerializer(serializers.Serializer):
    """Envoi manuel depuis le back-office (message ciblé)."""

    recipients = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)
    notification_type = serializers.CharField(default="SYSTEM")
    title = serializers.CharField(max_length=180)
    body = serializers.CharField()
    action_url = serializers.CharField(required=False, allow_blank=True)
    also_sms = serializers.BooleanField(default=False)
