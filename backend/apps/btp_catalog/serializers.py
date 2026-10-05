"""Serializers du catalogue de réalisations."""
from __future__ import annotations

from rest_framework import serializers

from apps.companies.models import Specialty
from apps.btp_catalog.models import Realization, RealizationMedia
from common.serializers import AssetSerializer, LocationSerializer
from common.utils import humanize_amount


class RealizationMediaSerializer(serializers.ModelSerializer):
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    medium_url = serializers.SerializerMethodField()

    class Meta:
        model = RealizationMedia
        fields = ("id", "kind", "kind_label", "asset", "url", "thumbnail_url", "medium_url", "caption", "order")

    def get_url(self, obj: RealizationMedia) -> str:
        return obj.asset.large_url

    def get_thumbnail_url(self, obj: RealizationMedia) -> str:
        return obj.asset.thumbnail_url

    def get_medium_url(self, obj: RealizationMedia) -> str:
        return obj.asset.medium_url


class RealizationListSerializer(serializers.ModelSerializer):
    type_label = serializers.CharField(source="get_realization_type_display", read_only=True)
    company_name = serializers.CharField(source="company.name", read_only=True)
    company_slug = serializers.CharField(source="company.slug", read_only=True)
    company_verified = serializers.BooleanField(source="company.is_verified", read_only=True)
    display_location = serializers.CharField(read_only=True)
    cover_url = serializers.CharField(read_only=True)
    services = serializers.SerializerMethodField()
    budget_display = serializers.SerializerMethodField()

    class Meta:
        model = Realization
        fields = (
            "id", "title", "slug", "realization_type", "type_label", "company_name",
            "company_slug", "company_verified", "display_location", "year", "surface_m2",
            "duration_days", "cover_url", "services", "budget_display", "is_featured",
            "views_count", "created_at",
        )

    def get_services(self, obj: Realization) -> list[str]:
        cache = getattr(obj, "services_cache", None)
        if cache is None:
            cache = list(obj.services.all())
        return [item.name for item in cache]

    def get_budget_display(self, obj: Realization) -> str:
        if not (obj.budget_visible and obj.budget_xaf):
            return ""
        return humanize_amount(obj.budget_xaf)


class RealizationDetailSerializer(RealizationListSerializer):
    company = serializers.SerializerMethodField()
    location_detail = LocationSerializer(source="location", read_only=True)
    media = RealizationMediaSerializer(many=True, read_only=True)
    before_after = serializers.SerializerMethodField()

    class Meta(RealizationListSerializer.Meta):
        fields = RealizationListSerializer.Meta.fields + (
            "description", "levels_count", "rooms_count", "client_testimonial", "client_name",
            "budget_xaf", "budget_visible", "company", "location_detail", "media",
            "before_after", "status",
        )

    def get_company(self, obj: Realization) -> dict:
        return {
            "id": obj.company_id,
            "name": obj.company.name,
            "slug": obj.company.slug,
            "city": obj.company.city,
            "verified": obj.company.is_verified,
            "rating": float(obj.company.rating_average or 0),
            "rating_count": obj.company.rating_count,
            "logo_url": obj.company.logo_url,
            "years_experience": obj.company.years_experience,
            "phone": obj.company.phone,
            "projects_count": obj.company.projects_count,
        }

    def get_before_after(self, obj: Realization) -> dict:
        data = obj.before_after
        return {
            "before": RealizationMediaSerializer(data["before"], many=True).data,
            "after": RealizationMediaSerializer(data["after"], many=True).data,
        }


class RealizationWriteSerializer(serializers.ModelSerializer):
    services = serializers.PrimaryKeyRelatedField(
        queryset=Specialty.objects.filter(is_active=True), many=True, required=False
    )
    media = serializers.ListField(child=serializers.DictField(), required=False, write_only=True)

    class Meta:
        model = Realization
        fields = (
            "id", "title", "realization_type", "location", "location_text", "country", "year",
            "description", "surface_m2", "levels_count", "rooms_count", "duration_days",
            "budget_xaf", "budget_visible", "client_testimonial", "client_name", "services",
            "cover", "order", "media",
        )

    def validate_year(self, value: int | None) -> int | None:
        from django.utils import timezone

        if value and value > timezone.localdate().year:
            raise serializers.ValidationError("L'année ne peut pas être dans le futur.")
        return value

    def validate_description(self, value: str) -> str:
        if value and len(value.strip()) < 60:
            raise serializers.ValidationError(
                "Décrivez la réalisation en quelques phrases (60 caractères minimum) : "
                "c'est ce qui convaincra les clients."
            )
        return value


class RealizationAdminSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    type_label = serializers.CharField(source="get_realization_type_display", read_only=True)

    class Meta:
        model = Realization
        fields = (
            "id", "title", "slug", "company", "company_name", "realization_type", "type_label",
            "location_text", "year", "status", "status_label", "is_featured", "views_count",
            "created_at", "updated_at",
        )
        read_only_fields = ("views_count",)
