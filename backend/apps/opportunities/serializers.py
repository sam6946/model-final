"""Serializers des opportunités BTP."""
from __future__ import annotations

from rest_framework import serializers

from apps.companies.serializers import SpecialtySerializer
from apps.opportunities.models import Opportunity
from common.utils import humanize_amount


class OpportunityListSerializer(serializers.ModelSerializer):
    property_type_label = serializers.SerializerMethodField()
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    display_location = serializers.CharField(read_only=True)
    budget_label = serializers.CharField(read_only=True)
    is_open = serializers.BooleanField(read_only=True)
    days_left = serializers.IntegerField(read_only=True)
    specialties = SpecialtySerializer(source="required_specialties", many=True, read_only=True)
    eligible_for_me = serializers.SerializerMethodField()
    already_applied = serializers.SerializerMethodField()

    class Meta:
        model = Opportunity
        fields = (
            "id", "reference", "title", "slug", "description", "property_type",
            "property_type_label", "display_location", "country", "budget_min_xaf",
            "budget_max_xaf", "budget_label", "budget_visible", "start_date", "duration_days",
            "application_deadline", "minimum_experience_years", "requires_verified_company",
            "status", "status_label", "visibility", "is_featured", "is_open", "days_left",
            "specialties", "applications_count", "views_count", "published_at", "created_at",
            "eligible_for_me", "already_applied",
        )

    def get_property_type_label(self, obj: Opportunity) -> str:
        return dict(Opportunity._meta.get_field("property_type").choices).get(
            obj.property_type, obj.property_type
        )

    def _company(self, obj: Opportunity):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return None
        return getattr(user, "primary_company", None)

    def get_eligible_for_me(self, obj: Opportunity) -> bool | None:
        company = self._company(obj)
        if company is None:
            return None
        if obj.requires_verified_company and not company.is_verified:
            return False
        if obj.minimum_experience_years and company.years_experience < obj.minimum_experience_years:
            return False
        required = set(obj.required_specialties.values_list("id", flat=True))
        if required:
            mine = set(company.specialties.values_list("id", flat=True))
            if not required & mine:
                return False
        return True

    def get_already_applied(self, obj: Opportunity) -> bool:
        company = self._company(obj)
        if company is None:
            return False
        cache = getattr(obj, "applied_company_ids", None)
        if cache is not None:
            return company.pk in cache
        return obj.applications.filter(company=company).exists()


class OpportunityDetailSerializer(OpportunityListSerializer):
    scope_of_work = serializers.CharField(read_only=True)
    required_documents = serializers.JSONField(read_only=True)
    site_available_for_visit = serializers.BooleanField(read_only=True)
    budget_min_label = serializers.SerializerMethodField()
    budget_max_label = serializers.SerializerMethodField()

    class Meta(OpportunityListSerializer.Meta):
        fields = OpportunityListSerializer.Meta.fields + (
            "scope_of_work", "required_documents", "site_available_for_visit",
            "budget_min_label", "budget_max_label",
        )

    def get_budget_min_label(self, obj: Opportunity) -> str:
        return humanize_amount(obj.budget_min_xaf) if obj.budget_min_xaf else ""

    def get_budget_max_label(self, obj: Opportunity) -> str:
        return humanize_amount(obj.budget_max_xaf) if obj.budget_max_xaf else ""


class OpportunityWriteSerializer(serializers.ModelSerializer):
    required_specialties = serializers.PrimaryKeyRelatedField(many=True, required=False, read_only=True)

    class Meta:
        model = Opportunity
        fields = (
            "title", "description", "scope_of_work", "required_documents", "property_type",
            "location", "location_text", "country", "site_available_for_visit",
            "budget_min_xaf", "budget_max_xaf", "budget_visible", "start_date", "duration_days",
            "application_deadline", "minimum_experience_years", "requires_verified_company",
            "status", "visibility", "is_featured", "project", "client_name", "client_contact",
            "internal_notes", "required_specialties",
        )

    def validate(self, attrs):
        from django.utils import timezone

        deadline = attrs.get("application_deadline") or getattr(self.instance, "application_deadline", None)
        if deadline and deadline < timezone.localdate() and attrs.get("status") == "OPEN":
            raise serializers.ValidationError({
                "application_deadline": "La date limite est déjà passée : corrigez-la avant d'ouvrir les candidatures."
            })
        budget_min = attrs.get("budget_min_xaf") or getattr(self.instance, "budget_min_xaf", None)
        budget_max = attrs.get("budget_max_xaf") or getattr(self.instance, "budget_max_xaf", None)
        if budget_min and budget_max and budget_min > budget_max:
            raise serializers.ValidationError({
                "budget_max_xaf": "Le budget maximum doit être supérieur au minimum."
            })
        if not (attrs.get("location_text") or attrs.get("location")):
            raise serializers.ValidationError({
                "location_text": "Indiquez la localisation du marché (ville ou quartier)."
            })
        return attrs
