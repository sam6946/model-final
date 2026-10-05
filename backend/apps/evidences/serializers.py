"""Serializers des preuves terrain (dont la synchronisation hors ligne)."""
from __future__ import annotations

from rest_framework import serializers

from apps.evidences.models import Evidence, EvidenceComment, EvidenceKind
from common.serializers import AssetSerializer


class EvidenceCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.full_name", read_only=True, default="KEMTA")
    author_initials = serializers.CharField(source="author.initials", read_only=True, default="KE")

    class Meta:
        model = EvidenceComment
        fields = ("id", "author_name", "author_initials", "body", "is_internal", "created_at")
        read_only_fields = ("created_at",)


class EvidenceSerializer(serializers.ModelSerializer):
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    thumbnail_url = serializers.CharField(read_only=True)
    preview_url = serializers.CharField(read_only=True)
    asset_detail = AssetSerializer(source="asset", read_only=True)
    captured_by_name = serializers.CharField(source="captured_by.full_name", read_only=True, default="")
    validated_by_name = serializers.CharField(source="validated_by.full_name", read_only=True, default="")
    phase_name = serializers.CharField(source="phase.name", read_only=True, default="")
    freshness_label = serializers.CharField(read_only=True)
    is_location_suspect = serializers.BooleanField(read_only=True)

    class Meta:
        model = Evidence
        fields = (
            "id", "project", "property", "phase", "phase_name", "task", "kind", "kind_label",
            "title", "caption", "note", "asset", "asset_detail", "thumbnail_url", "preview_url",
            "measurements", "captured_at", "captured_by", "captured_by_name", "capture_device",
            "latitude", "longitude", "accuracy_meters", "distance_to_site_m", "is_offline_capture",
            "client_uuid", "status", "status_label", "validated_by_name", "validated_at",
            "rejection_reason", "is_visible_to_customer", "is_pinned", "freshness_label",
            "is_location_suspect", "created_at",
        )
        read_only_fields = (
            "status", "validated_by_name", "validated_at", "rejection_reason", "created_at",
            "distance_to_site_m",
        )


class EvidenceCreateSerializer(serializers.Serializer):
    """Dépôt d'une preuve : photo/vidéo/note, avec ou sans position GPS."""

    project = serializers.IntegerField(required=False, allow_null=True)
    property = serializers.IntegerField(required=False, allow_null=True)
    phase = serializers.IntegerField(required=False, allow_null=True)
    task = serializers.IntegerField(required=False, allow_null=True)
    kind = serializers.ChoiceField(choices=EvidenceKind.choices, default=EvidenceKind.PHOTO)
    title = serializers.CharField(max_length=180, required=False, allow_blank=True)
    caption = serializers.CharField(max_length=255, required=False, allow_blank=True)
    note = serializers.CharField(required=False, allow_blank=True, max_length=4000)
    asset = serializers.IntegerField(required=False, allow_null=True)
    measurements = serializers.JSONField(required=False, default=dict)
    captured_at = serializers.DateTimeField(required=False, allow_null=True)
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    accuracy_meters = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    capture_device = serializers.CharField(max_length=120, required=False, allow_blank=True)
    is_offline_capture = serializers.BooleanField(default=False)
    client_uuid = serializers.UUIDField(required=False)

    def validate(self, attrs):
        if not attrs.get("project") and not attrs.get("property"):
            raise serializers.ValidationError({
                "project": "Indiquez le chantier ou la propriété concernée par cette preuve."
            })
        if attrs.get("kind") in {EvidenceKind.PHOTO, EvidenceKind.VIDEO, EvidenceKind.DOCUMENT} and not attrs.get("asset"):
            raise serializers.ValidationError({
                "asset": "Le fichier de la preuve est manquant. Réessayez l'envoi depuis l'application."
            })
        if attrs.get("kind") == EvidenceKind.NOTE and not (attrs.get("note") or attrs.get("title")):
            raise serializers.ValidationError({
                "note": "Écrivez votre observation avant d'enregistrer."
            })
        if attrs.get("captured_at"):
            from django.utils import timezone

            if attrs["captured_at"] > timezone.now():
                # Une photo « prise demain » est un signe d'horloge déréglée :
                # on corrige plutôt que de rejeter (terrain hors ligne).
                attrs["captured_at"] = timezone.now()
        return attrs


class EvidenceBulkItemSerializer(EvidenceCreateSerializer):
    """Un élément d'un lot synchronisé depuis la PWA."""

    client_uuid = serializers.UUIDField(required=True)


class EvidenceBulkSerializer(serializers.Serializer):
    items = EvidenceBulkItemSerializer(many=True, allow_empty=False)

    def validate_items(self, value: list) -> list:
        if len(value) > 60:
            raise serializers.ValidationError(
                "Vous ne pouvez synchroniser que 60 éléments à la fois. "
                "Relancez la synchronisation pour le reste."
            )
        return value


class EvidenceReviewSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["validate", "reject"])
    comment = serializers.CharField(required=False, allow_blank=True, max_length=255)

    def validate(self, attrs):
        if attrs["action"] == "reject" and not (attrs.get("comment") or "").strip():
            raise serializers.ValidationError({
                "comment": "Indiquez le motif du refus : le technicien terrain doit comprendre la correction attendue."
            })
        return attrs
