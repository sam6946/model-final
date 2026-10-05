"""Serializers transverses : localisations, fichiers, contenus publics."""
from __future__ import annotations

from rest_framework import serializers

from common.constants import UploadKind
from common.models import Asset, FAQItem, Location, Testimonial, TrustStat


class LocationSerializer(serializers.ModelSerializer):
    label = serializers.CharField(read_only=True)

    class Meta:
        model = Location
        fields = ("id", "name", "slug", "region", "country", "kind", "label", "latitude", "longitude")


class AssetSerializer(serializers.ModelSerializer):
    """Expose uniquement des URLs (les clés S3 ne sortent pas du backend)."""

    url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    medium_url = serializers.SerializerMethodField()
    large_url = serializers.SerializerMethodField()

    class Meta:
        model = Asset
        fields = (
            "id", "kind", "status", "original_filename", "mime_type", "size_bytes",
            "width", "height", "url", "thumbnail_url", "medium_url", "large_url",
            "created_at",
        )

    def get_url(self, obj: Asset) -> str:
        return obj.url

    def get_thumbnail_url(self, obj: Asset) -> str:
        return obj.thumbnail_url

    def get_medium_url(self, obj: Asset) -> str:
        return obj.medium_url

    def get_large_url(self, obj: Asset) -> str:
        return obj.variant_url("large")


class PresignRequestSerializer(serializers.Serializer):
    upload_kind = serializers.ChoiceField(choices=UploadKind.choices)
    filename = serializers.CharField(max_length=255)
    content_type = serializers.CharField(max_length=120, required=False, allow_blank=True)
    size = serializers.IntegerField(min_value=1)


class PresignResponseSerializer(serializers.Serializer):
    upload_url = serializers.CharField()
    method = serializers.CharField()
    key = serializers.CharField()
    fields = serializers.DictField()
    headers = serializers.DictField()
    expires_in = serializers.IntegerField()


class FAQItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQItem
        fields = ("id", "category", "question", "answer", "order")


class TestimonialSerializer(serializers.ModelSerializer):
    photo_url = serializers.SerializerMethodField()
    project_name = serializers.CharField(source="project.name", read_only=True, default="")

    class Meta:
        model = Testimonial
        fields = (
            "id", "author_name", "author_role", "author_city", "author_country",
            "quote", "rating", "photo_url", "project_name",
        )

    def get_photo_url(self, obj: Testimonial) -> str:
        return obj.photo.medium_url if obj.photo else ""


class TrustStatSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrustStat
        fields = ("id", "label", "value", "hint", "icon")
