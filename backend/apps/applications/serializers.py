"""Serializers des candidatures BTP."""
from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers

from apps.applications.models import Application, ApplicationDocument
from common.serializers import AssetSerializer


class ApplicationDocumentSerializer(serializers.ModelSerializer):
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    asset_detail = AssetSerializer(source="asset", read_only=True)

    class Meta:
        model = ApplicationDocument
        fields = ("id", "kind", "kind_label", "title", "asset", "asset_detail", "created_at")
        read_only_fields = ("created_at",)


class ApplicationListSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    company_name = serializers.CharField(source="company.name", read_only=True)
    company_slug = serializers.CharField(source="company.slug", read_only=True)
    company_verified = serializers.BooleanField(source="company.is_verified", read_only=True)
    company_rating = serializers.FloatField(source="company.rating_average", read_only=True)
    opportunity_title = serializers.CharField(source="opportunity.title", read_only=True)
    opportunity_slug = serializers.CharField(source="opportunity.slug", read_only=True)
    opportunity_reference = serializers.CharField(source="opportunity.reference", read_only=True)
    location = serializers.CharField(source="opportunity.display_location", read_only=True)
    budget_label = serializers.SerializerMethodField()
    is_decided = serializers.BooleanField(read_only=True)
    status_is_positive = serializers.BooleanField(read_only=True)

    class Meta:
        model = Application
        fields = (
            "id", "reference", "opportunity", "opportunity_title", "opportunity_slug",
            "opportunity_reference", "location", "company", "company_name", "company_slug",
            "company_verified", "company_rating", "status", "status_label",
            "estimated_budget_xaf", "budget_label", "proposed_duration_days", "score",
            "is_decided", "status_is_positive", "created_at", "updated_at",
        )

    def get_budget_label(self, obj: Application) -> str:
        from common.utils import humanize_amount

        return humanize_amount(obj.estimated_budget_xaf) if obj.estimated_budget_xaf else "Non chiffré"


class ApplicationDetailSerializer(ApplicationListSerializer):
    documents = ApplicationDocumentSerializer(many=True, read_only=True)
    realizations = serializers.SerializerMethodField()
    opportunity_summary = serializers.SerializerMethodField()

    class Meta(ApplicationListSerializer.Meta):
        fields = ApplicationListSerializer.Meta.fields + (
            "presentation", "similar_experience", "methodology", "team_size",
            "team_composition", "message", "accepts_site_visit", "contact_override",
            "internal_notes", "client_feedback", "rejection_reason", "reviewed_at",
            "documents", "realizations", "opportunity_summary",
        )

    def get_realizations(self, obj: Application) -> list:
        return [
            {
                "id": item.pk,
                "title": item.title,
                "slug": item.slug,
                "type": item.get_realization_type_display(),
                "location": item.display_location,
                "year": item.year,
                "cover_url": item.cover_url,
            }
            for item in obj.relevant_realizations.select_related("cover").all()
        ]

    def get_opportunity_summary(self, obj: Application) -> dict:
        opportunity = obj.opportunity
        return {
            "reference": opportunity.reference,
            "title": opportunity.title,
            "location": opportunity.display_location,
            "budget_label": opportunity.budget_label,
            "deadline": opportunity.application_deadline,
            "status": opportunity.status,
        }


class ApplicationCreateSerializer(serializers.Serializer):
    """Formulaire de candidature : complet mais sans friction inutile."""

    presentation = serializers.CharField(
        max_length=6000,
        error_messages={
            "blank": "Présentez votre entreprise et votre motivation pour ce marché.",
            "required": "Présentez votre entreprise et votre motivation pour ce marché.",
        },
    )
    similar_experience = serializers.CharField(required=False, allow_blank=True, max_length=6000)
    methodology = serializers.CharField(required=False, allow_blank=True, max_length=6000)
    estimated_budget_xaf = serializers.DecimalField(
        max_digits=14, decimal_places=2, required=False, allow_null=True, min_value=Decimal("0")
    )
    proposed_duration_days = serializers.IntegerField(required=False, allow_null=True, min_value=1, max_value=3650)
    team_size = serializers.IntegerField(required=False, allow_null=True, min_value=1, max_value=5000)
    team_composition = serializers.CharField(required=False, allow_blank=True, max_length=255)
    message = serializers.CharField(required=False, allow_blank=True, max_length=4000)
    accepts_site_visit = serializers.BooleanField(default=True)
    contact_override = serializers.CharField(required=False, allow_blank=True, max_length=180)
    realization_ids = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
    document_ids = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
    document_kinds = serializers.DictField(child=serializers.CharField(), required=False, default=dict)

    def validate_presentation(self, value: str) -> str:
        if len(value.strip()) < 80:
            raise serializers.ValidationError(
                "Détaillez un peu plus votre présentation (80 caractères minimum) : "
                "c'est le premier critère d'analyse du client."
            )
        return value.strip()


class ApplicationReviewSerializer(serializers.Serializer):
    """Instruction d'une candidature par l'équipe KEMTA."""

    status = serializers.ChoiceField(choices=Application._meta.get_field("status").choices)
    score = serializers.DecimalField(
        max_digits=4, decimal_places=2, required=False, allow_null=True,
        min_value=Decimal("0"), max_value=Decimal("100"),
    )
    internal_notes = serializers.CharField(required=False, allow_blank=True, max_length=6000)
    client_feedback = serializers.CharField(required=False, allow_blank=True, max_length=6000)
    rejection_reason = serializers.CharField(required=False, allow_blank=True, max_length=255)

    def validate(self, attrs):
        from apps.applications.models import ApplicationStatus

        if attrs["status"] == ApplicationStatus.REJECTED and not (attrs.get("rejection_reason") or "").strip():
            raise serializers.ValidationError({
                "rejection_reason": "Indiquez le motif : l'entreprise doit comprendre la décision."
            })
        return attrs
