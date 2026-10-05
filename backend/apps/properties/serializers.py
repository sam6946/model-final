"""Serializers des propriétés et de leur galerie photo."""
from __future__ import annotations

from rest_framework import serializers

from apps.properties.models import Property, PropertyPhoto
from common.serializers import AssetSerializer, LocationSerializer


class PropertyPhotoSerializer(serializers.ModelSerializer):
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = PropertyPhoto
        fields = ("id", "kind", "kind_label", "asset", "url", "thumbnail_url", "caption", "taken_at", "order")
        read_only_fields = ("taken_at",)

    def get_url(self, obj: PropertyPhoto) -> str:
        return obj.asset.medium_url

    def get_thumbnail_url(self, obj: PropertyPhoto) -> str:
        return obj.asset.thumbnail_url


class PropertyListSerializer(serializers.ModelSerializer):
    type_label = serializers.CharField(source="get_property_type_display", read_only=True)
    occupancy_label = serializers.CharField(source="get_occupancy_status_display", read_only=True)
    display_location = serializers.CharField(read_only=True)
    cover_url = serializers.CharField(read_only=True)
    needs_attention = serializers.BooleanField(read_only=True)
    days_since_last_visit = serializers.IntegerField(read_only=True)
    active_contract_label = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = (
            "id", "reference", "name", "property_type", "type_label", "occupancy_status",
            "occupancy_label", "display_location", "city", "cover_url", "area_m2",
            "rooms_count", "last_visited_at", "next_visit_at", "needs_attention",
            "days_since_last_visit", "condition_score", "active_contract_label", "is_active",
            "created_at",
        )

    def get_active_contract_label(self, obj: Property) -> str:
        contract = obj.active_contract
        if contract is None:
            return ""
        return f"{contract.get_frequency_display()} — {contract.reference}"


class PropertyDetailSerializer(serializers.ModelSerializer):
    type_label = serializers.CharField(source="get_property_type_display", read_only=True)
    occupancy_label = serializers.CharField(source="get_occupancy_status_display", read_only=True)
    display_location = serializers.CharField(read_only=True)
    cover_url = serializers.CharField(read_only=True)
    needs_attention = serializers.BooleanField(read_only=True)
    location_detail = LocationSerializer(source="location", read_only=True)
    photos = PropertyPhotoSerializer(many=True, read_only=True)
    manager_name = serializers.CharField(source="manager.full_name", read_only=True, default="")
    open_issues_count = serializers.SerializerMethodField()
    contracts_count = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = (
            "id", "reference", "name", "property_type", "type_label", "occupancy_status",
            "occupancy_label", "location_detail", "location_text", "display_location",
            "address", "city", "country", "latitude", "longitude", "area_m2", "land_area_m2",
            "rooms_count", "bedrooms_count", "bathrooms_count", "levels_count", "year_built",
            "tenant_name", "tenant_phone", "has_guardian", "is_fenced", "has_water",
            "has_electricity", "has_security_system", "documentation_status",
            "title_deed_number", "estimated_value_xaf", "monthly_rent_xaf", "cover",
            "cover_url", "description", "internal_notes", "last_visited_at",
            "last_inspection_at", "next_visit_at", "condition_score", "manager_name",
            "needs_attention", "open_issues_count", "contracts_count", "photos", "is_active",
            "created_at", "updated_at",
        )
        read_only_fields = ("reference", "created_at", "updated_at")

    def get_open_issues_count(self, obj: Property) -> int:
        return obj.issues.exclude(status__in=["RESOLVED", "CLOSED"]).count()

    def get_contracts_count(self, obj: Property) -> int:
        return obj.maintenance_contracts.count()


class PropertyWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Property
        fields = (
            "name", "property_type", "location", "location_text", "address", "city", "country",
            "latitude", "longitude", "area_m2", "land_area_m2", "rooms_count", "bedrooms_count",
            "bathrooms_count", "levels_count", "year_built", "occupancy_status", "tenant_name",
            "tenant_phone", "has_guardian", "is_fenced", "has_water", "has_electricity",
            "has_security_system", "documentation_status", "title_deed_number",
            "estimated_value_xaf", "monthly_rent_xaf", "cover", "description", "internal_notes",
            "manager", "is_active",
        )
        extra_kwargs = {"owner": {"required": False}}
