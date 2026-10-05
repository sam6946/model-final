"""Serializers de l'entretien immobilier : contrats, visites, problèmes."""
from __future__ import annotations

from rest_framework import serializers

from apps.maintenance.models import (
    MaintenanceContract,
    MaintenanceIssue,
    MaintenanceServiceType,
    MaintenanceVisit,
)


class MaintenanceServiceTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceServiceType
        fields = ("id", "code", "name", "description", "icon", "base_price_xaf", "unit", "requires_technician")


class MaintenanceVisitSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    technician_name = serializers.CharField(source="technician.full_name", read_only=True, default="")
    property_name = serializers.CharField(source="property.name", read_only=True)
    property_reference = serializers.CharField(source="property.reference", read_only=True)
    services = MaintenanceServiceTypeSerializer(source="services_performed", many=True, read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    checklist_done_ratio = serializers.FloatField(read_only=True)

    class Meta:
        model = MaintenanceVisit
        fields = (
            "id", "reference", "contract", "property", "property_name", "property_reference",
            "scheduled_for", "estimated_duration_minutes", "completed_at", "status",
            "status_label", "technician", "technician_name", "services", "checklist",
            "report", "customer_visible_report", "recommendations", "issues_found",
            "condition_score", "cost_xaf", "access_notes", "photos_count", "is_overdue",
            "checklist_done_ratio", "created_at",
        )
        read_only_fields = ("reference", "completed_at", "created_at")


class MaintenanceIssueSerializer(serializers.ModelSerializer):
    severity_label = serializers.CharField(source="get_severity_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    property_name = serializers.CharField(source="property.name", read_only=True)
    is_urgent = serializers.BooleanField(read_only=True)
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = MaintenanceIssue
        fields = (
            "id", "property", "property_name", "visit", "title", "description", "severity",
            "severity_label", "status", "status_label", "estimate_xaf", "photo", "photo_url",
            "reported_by", "resolved_at", "resolution_notes", "is_urgent", "created_at",
        )
        read_only_fields = ("resolved_at", "created_at")

    def get_photo_url(self, obj: MaintenanceIssue) -> str:
        return obj.photo.medium_url if obj.photo_id else ""


class MaintenanceContractSerializer(serializers.ModelSerializer):
    frequency_label = serializers.CharField(source="get_frequency_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    services = MaintenanceServiceTypeSerializer(many=True, read_only=True)
    property_name = serializers.CharField(source="property.name", read_only=True)
    property_reference = serializers.CharField(source="property.reference", read_only=True)
    monthly_price_xaf = serializers.FloatField(read_only=True)
    next_visit_date = serializers.SerializerMethodField()
    visits_count = serializers.SerializerMethodField()

    class Meta:
        model = MaintenanceContract
        fields = (
            "id", "reference", "property", "property_name", "property_reference", "customer",
            "frequency", "frequency_label", "services", "status", "status_label", "start_date",
            "end_date", "price_xaf", "monthly_price_xaf", "billing_cycle_months", "visits_included",
            "auto_generate_visits", "assigned_team", "instructions", "next_visit_date",
            "visits_count", "created_at", "updated_at",
        )
        read_only_fields = ("reference", "customer", "created_at", "updated_at")

    def get_next_visit_date(self, obj: MaintenanceContract):
        visit = obj.next_visit
        return visit.scheduled_for if visit else None

    def get_visits_count(self, obj: MaintenanceContract) -> int:
        return getattr(obj, "visits_count_cache", None) or obj.visits.count()


class MaintenanceContractCreateSerializer(serializers.Serializer):
    property = serializers.IntegerField()
    frequency = serializers.ChoiceField(choices=MaintenanceContract._meta.get_field("frequency").choices)
    service_ids = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
    price_xaf = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False, allow_null=True)
    billing_cycle_months = serializers.IntegerField(min_value=1, max_value=12, default=1)
    visits_included = serializers.IntegerField(min_value=1, max_value=12, default=1)
    assigned_team = serializers.IntegerField(required=False, allow_null=True)
    instructions = serializers.CharField(required=False, allow_blank=True)
    auto_generate_visits = serializers.BooleanField(default=True)

    def validate_service_ids(self, value: list) -> list:
        if not value:
            return value
        valid = set(MaintenanceServiceType.objects.filter(id__in=value, is_active=True).values_list("id", flat=True))
        missing = set(value) - valid
        if missing:
            raise serializers.ValidationError("Une des prestations sélectionnées n'est plus disponible.")
        return value
