"""Serializers des demandes de service (création publique + suivi interne)."""
from __future__ import annotations

from rest_framework import serializers

from apps.service_requests.models import (
    ServiceCatalog,
    ServiceKind,
    ServiceRequest,
    ServiceRequestAttachment,
    ServiceRequestEvent,
)
from apps.service_requests.schemas import validate_payload_for_kind
from common.serializers import AssetSerializer, LocationSerializer
from common.utils import format_phone_display


class ServiceRequestAttachmentSerializer(serializers.ModelSerializer):
    asset_detail = AssetSerializer(source="asset", read_only=True)

    class Meta:
        model = ServiceRequestAttachment
        fields = ("id", "category", "asset", "asset_detail", "caption", "created_at")
        read_only_fields = ("created_at",)


class ServiceRequestEventSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source="actor.full_name", read_only=True, default="Équipe KEMTA")
    status_label = serializers.SerializerMethodField()

    class Meta:
        model = ServiceRequestEvent
        fields = (
            "id", "from_status", "to_status", "status_label", "comment", "actor_name",
            "is_customer_visible", "created_at",
        )

    def get_status_label(self, obj: ServiceRequestEvent) -> str:
        if not obj.to_status:
            return "Note"
        return dict(ServiceRequest._meta.get_field("status").choices).get(obj.to_status, obj.to_status)


class ServiceRequestCreateSerializer(serializers.Serializer):
    """Formulaire multi-étapes : validation stricte, messages lisibles."""

    kind = serializers.ChoiceField(
        choices=ServiceKind.choices,
        error_messages={"invalid_choice": "Veuillez choisir le service dont vous avez besoin."},
    )
    first_name = serializers.CharField(
        max_length=80,
        error_messages={"blank": "Veuillez renseigner votre prénom.", "required": "Veuillez renseigner votre prénom."},
    )
    last_name = serializers.CharField(
        max_length=80,
        error_messages={"blank": "Veuillez renseigner votre nom.", "required": "Veuillez renseigner votre nom."},
    )
    phone = serializers.CharField(
        max_length=24,
        error_messages={
            "blank": "Veuillez renseigner votre numéro de téléphone.",
            "required": "Veuillez renseigner votre numéro de téléphone.",
        },
    )
    email = serializers.EmailField(
        required=False, allow_blank=True,
        error_messages={"invalid": "Cette adresse e-mail ne semble pas valide (elle reste facultative)."},
    )
    country = serializers.CharField(max_length=2, required=False, default="CM")
    city = serializers.CharField(max_length=120, required=False, allow_blank=True)
    city_of_residence = serializers.CharField(max_length=120, required=False, allow_blank=True)

    project_type = serializers.CharField(max_length=80, required=False, allow_blank=True)
    location_id = serializers.IntegerField(required=False, allow_null=True)
    location_text = serializers.CharField(max_length=200, required=False, allow_blank=True)
    budget_min_xaf = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    budget_max_xaf = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    spent_xaf = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    desired_start_date = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    description = serializers.CharField(required=False, allow_blank=True, max_length=4000)
    current_progress = serializers.CharField(max_length=120, required=False, allow_blank=True)
    current_company = serializers.CharField(max_length=180, required=False, allow_blank=True)
    site_manager = serializers.CharField(max_length=180, required=False, allow_blank=True)
    known_issues = serializers.CharField(required=False, allow_blank=True, max_length=4000)
    objective = serializers.CharField(required=False, allow_blank=True, max_length=4000)
    maintenance_services = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    maintenance_frequency = serializers.CharField(max_length=20, required=False, allow_blank=True)
    property_type = serializers.CharField(max_length=40, required=False, allow_blank=True)
    property_occupied = serializers.CharField(max_length=20, required=False, allow_blank=True)
    last_visit_date = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    service_id = serializers.IntegerField(required=False, allow_null=True)
    payload = serializers.JSONField(required=False, default=dict)
    source = serializers.CharField(max_length=40, required=False, allow_blank=True)
    utm = serializers.JSONField(required=False, default=dict)
    attachment_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, default=list, max_length=25
    )
    terms_accepted = serializers.BooleanField(
        error_messages={"required": "Veuillez accepter le traitement de vos données pour envoyer votre demande."}
    )

    def validate_phone(self, value: str) -> str:
        from common.utils import normalize_phone

        try:
            return normalize_phone(value)
        except ValueError as exc:
            raise serializers.ValidationError(
                "Ce numéro de téléphone n'est pas valide. Exemple : +237 6 99 11 22 33."
            ) from exc

    def validate_first_name(self, value: str) -> str:
        if len(value.strip()) < 2:
            raise serializers.ValidationError("Le prénom doit contenir au moins 2 caractères.")
        return value.strip()

    def validate_last_name(self, value: str) -> str:
        if len(value.strip()) < 2:
            raise serializers.ValidationError("Le nom doit contenir au moins 2 caractères.")
        return value.strip()

    def validate(self, attrs):
        if not attrs.get("terms_accepted"):
            raise serializers.ValidationError({
                "terms_accepted": "Veuillez accepter le traitement de vos données pour continuer."
            })
        attrs["email"] = (attrs.get("email") or "").strip().lower()
        attrs["payload"] = validate_payload_for_kind(attrs["kind"], attrs.get("payload") or {}, attrs)

        location_id = attrs.get("location_id")
        if location_id:
            from common.models import Location

            if not Location.objects.filter(pk=location_id, is_active=True).exists():
                raise serializers.ValidationError({"location_id": "Cette localisation n'est pas reconnue."})
        if attrs["kind"] in {ServiceKind.BUILD_PROJECT, ServiceKind.EXISTING_SITE, ServiceKind.MAINTENANCE}:
            if not attrs.get("location_text") and not location_id:
                raise serializers.ValidationError({
                    "location_text": "Merci de préciser la ville ou le quartier concerné."
                })
        service_id = attrs.get("service_id")
        if service_id and not ServiceCatalog.objects.filter(pk=service_id, is_active=True).exists():
            raise serializers.ValidationError({"service_id": "Ce service n'est plus disponible."})
        return attrs


class ServiceRequestListSerializer(serializers.ModelSerializer):
    """Vue condensée pour les listes (client et back-office)."""

    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    budget_label = serializers.CharField(read_only=True)
    display_location = serializers.CharField(read_only=True)
    full_name = serializers.CharField(read_only=True)
    next_step_label = serializers.CharField(read_only=True)

    class Meta:
        model = ServiceRequest
        fields = (
            "id", "reference", "kind", "kind_label", "status", "status_label", "priority",
            "full_name", "phone", "city", "display_location", "budget_label",
            "desired_start_date", "created_at", "next_step_label", "estimated_value_xaf",
        )


class ServiceRequestDetailSerializer(serializers.ModelSerializer):
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    budget_label = serializers.CharField(read_only=True)
    display_location = serializers.CharField(read_only=True)
    full_name = serializers.CharField(read_only=True)
    next_step_label = serializers.CharField(read_only=True)
    phone_display = serializers.SerializerMethodField()
    location_detail = LocationSerializer(source="location", read_only=True)
    attachments = ServiceRequestAttachmentSerializer(many=True, read_only=True)
    events = serializers.SerializerMethodField()
    assigned_to_name = serializers.CharField(source="assigned_to.full_name", read_only=True, default="")
    converted_project_reference = serializers.CharField(source="converted_project.reference", read_only=True, default="")

    class Meta:
        model = ServiceRequest
        fields = (
            "id", "reference", "kind", "kind_label", "status", "status_label", "priority",
            "full_name", "first_name", "last_name", "phone", "phone_display", "email",
            "country", "city", "city_of_residence", "project_type", "location_text",
            "location_detail", "display_location", "budget_min_xaf", "budget_max_xaf",
            "budget_label", "spent_xaf", "desired_start_date", "description",
            "current_progress", "current_company", "site_manager", "known_issues",
            "objective", "maintenance_services", "maintenance_frequency", "property_type",
            "property_occupied", "last_visit_date", "payload", "source", "utm",
            "assigned_to_name", "internal_notes", "qualification_notes",
            "estimated_value_xaf", "scheduled_call_at", "first_contact_at",
            "converted_project_reference", "attachments", "events",
            "created_at", "updated_at", "next_step_label",
        )
        read_only_fields = ("reference", "created_at", "updated_at", "converted_project_reference")

    def get_phone_display(self, obj: ServiceRequest) -> str:
        return format_phone_display(obj.phone)

    def get_events(self, obj: ServiceRequest) -> list:
        events = list(obj.events.select_related("actor").all()[:30])
        return ServiceRequestEventSerializer(events, many=True).data


class ServiceRequestUpdateSerializer(serializers.ModelSerializer):
    """Mise à jour interne : statut, affectation, qualification."""

    class Meta:
        model = ServiceRequest
        fields = (
            "status", "priority", "assigned_to", "internal_notes", "estimated_value_xaf",
            "qualification_notes", "scheduled_call_at",
        )


class ServiceCatalogSerializer(serializers.ModelSerializer):
    hero_image_url = serializers.SerializerMethodField()

    class Meta:
        model = ServiceCatalog
        fields = (
            "id", "code", "name", "tagline", "description", "icon", "deliverables",
            "base_price_xaf", "duration_days", "requires_site_visit", "hero_image_url", "order",
        )

    def get_hero_image_url(self, obj: ServiceCatalog) -> str:
        return obj.hero_image.medium_url if obj.hero_image_id else ""
