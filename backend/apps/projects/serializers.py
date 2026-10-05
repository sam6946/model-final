"""Serializers des projets, phases, tâches, preuves et budgets."""
from __future__ import annotations

from rest_framework import serializers

from apps.construction.models import Phase, PhaseStatus
from apps.projects.models import (
    BudgetLine,
    Project,
    ProjectDocument,
    ProjectMember,
    ProjectStatus,
    ProjectUpdate,
    Task,
)
from common.serializers import AssetSerializer, LocationSerializer
from common.utils import humanize_amount


class PhaseSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(read_only=True)
    budget_planned_label = serializers.SerializerMethodField()
    budget_spent_label = serializers.SerializerMethodField()
    is_overdue = serializers.BooleanField(read_only=True)
    tasks_count = serializers.SerializerMethodField()
    evidences_count = serializers.SerializerMethodField()

    class Meta:
        model = Phase
        fields = (
            "id", "name", "description", "order", "weight_percent", "progress_percent",
            "status", "status_label", "planned_start", "planned_end", "actual_start",
            "actual_end", "budget_planned_xaf", "budget_spent_xaf", "budget_planned_label",
            "budget_spent_label", "budget_variance_xaf", "responsible", "blocked_reason",
            "is_overdue", "notes", "tasks_count", "evidences_count", "updated_at",
        )
        read_only_fields = ("updated_at",)

    def get_budget_planned_label(self, obj: Phase) -> str:
        return humanize_amount(obj.budget_planned_xaf) if obj.budget_planned_xaf else "—"

    def get_budget_spent_label(self, obj: Phase) -> str:
        return humanize_amount(obj.budget_spent_xaf) if obj.budget_spent_xaf else "—"

    def get_tasks_count(self, obj: Phase) -> int:
        return getattr(obj, "tasks_count_cache", None) or (obj.tasks.count() if obj.pk else 0)

    def get_evidences_count(self, obj: Phase) -> int:
        return getattr(obj, "evidences_count_cache", None) or 0


class PhaseWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Phase
        fields = (
            "name", "description", "order", "weight_percent", "progress_percent", "status",
            "planned_start", "planned_end", "actual_start", "actual_end",
            "budget_planned_xaf", "budget_spent_xaf", "responsible", "blocked_reason", "notes",
        )

    def validate(self, attrs):
        if attrs.get("planned_start") and attrs.get("planned_end"):
            if attrs["planned_end"] < attrs["planned_start"]:
                raise serializers.ValidationError({
                    "planned_end": "La date de fin doit être postérieure à la date de début."
                })
        return attrs


class TaskSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    priority_label = serializers.CharField(source="get_priority_display", read_only=True)
    assignee_name = serializers.CharField(source="assignee.full_name", read_only=True, default="")
    phase_name = serializers.CharField(source="phase.name", read_only=True, default="")
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = Task
        fields = (
            "id", "project", "phase", "phase_name", "title", "description", "assignee",
            "assignee_name", "status", "status_label", "priority", "priority_label", "due_date",
            "started_at", "completed_at", "requires_evidence", "progress_percent", "order",
            "is_overdue", "created_at", "updated_at",
        )
        read_only_fields = ("project", "completed_at", "started_at", "created_at", "updated_at")


class BudgetLineSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source="get_category_display", read_only=True)
    planned_label = serializers.SerializerMethodField()
    spent_label = serializers.SerializerMethodField()
    usage_percent = serializers.SerializerMethodField()
    is_overspent = serializers.BooleanField(read_only=True)

    class Meta:
        model = BudgetLine
        fields = (
            "id", "category", "category_label", "label", "planned_xaf", "committed_xaf",
            "spent_xaf", "planned_label", "spent_label", "usage_percent", "supplier",
            "notes", "is_overspent", "variance_xaf", "updated_at",
        )

    def get_planned_label(self, obj: BudgetLine) -> str:
        return humanize_amount(obj.planned_xaf)

    def get_spent_label(self, obj: BudgetLine) -> str:
        return humanize_amount(obj.spent_xaf)

    def get_usage_percent(self, obj: BudgetLine) -> float:
        from common.utils import percent

        return percent(obj.spent_xaf, obj.planned_xaf)


class ProjectMemberSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.full_name", read_only=True)
    user_phone = serializers.CharField(source="user.phone", read_only=True)
    user_initials = serializers.CharField(source="user.initials", read_only=True)
    role_label = serializers.CharField(source="get_role_display", read_only=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = ProjectMember
        fields = (
            "id", "user", "user_name", "user_phone", "user_initials", "role", "role_label",
            "can_capture_evidence", "can_validate_evidence", "can_view_finance",
            "can_manage_schedule", "receives_notifications", "is_active", "joined_at",
        )
        read_only_fields = ("joined_at",)


class ProjectDocumentSerializer(serializers.ModelSerializer):
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    asset_detail = AssetSerializer(source="asset", read_only=True)
    uploaded_by_name = serializers.CharField(source="uploaded_by.full_name", read_only=True, default="")

    class Meta:
        model = ProjectDocument
        fields = (
            "id", "kind", "kind_label", "title", "asset", "asset_detail", "visible_to_customer",
            "uploaded_by_name", "created_at",
        )
        read_only_fields = ("created_at",)


class ProjectUpdateSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.full_name", read_only=True, default="KEMTA")
    author_initials = serializers.CharField(source="author.initials", read_only=True, default="KE")
    type_label = serializers.CharField(source="get_update_type_display", read_only=True)

    class Meta:
        model = ProjectUpdate
        fields = (
            "id", "update_type", "type_label", "message", "payload", "author", "author_name",
            "author_initials", "visibility", "created_at",
        )
        read_only_fields = ("author", "created_at")


class ProjectListSerializer(serializers.ModelSerializer):
    """Vue cartes : ce que le client voit en arrivant sur son espace."""

    status_label = serializers.CharField(source="get_status_display", read_only=True)
    health_label = serializers.CharField(source="get_health_display", read_only=True)
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    display_location = serializers.CharField(read_only=True)
    cover_url = serializers.CharField(read_only=True)
    manager_name = serializers.CharField(source="manager.full_name", read_only=True, default="")
    company_name = serializers.CharField(source="company.name", read_only=True, default="")
    budget_label = serializers.SerializerMethodField()
    progress_percent = serializers.FloatField(source="physical_progress", read_only=True)
    budget_used_percent = serializers.FloatField(read_only=True)
    is_late = serializers.BooleanField(read_only=True)

    class Meta:
        model = Project
        fields = (
            "id", "reference", "name", "slug", "kind", "kind_label", "status", "status_label",
            "health", "health_label", "display_location", "cover_url", "manager_name",
            "company_name", "progress_percent", "budget_used_percent", "budget_label",
            "planned_start", "planned_end", "is_late", "updated_at", "created_at",
        )

    def get_budget_label(self, obj: Project) -> str:
        return humanize_amount(obj.budget_total_xaf, obj.currency) if obj.budget_total_xaf else "Budget à définir"


class ProjectDetailSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    health_label = serializers.CharField(source="get_health_display", read_only=True)
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    display_location = serializers.CharField(read_only=True)
    cover_url = serializers.CharField(read_only=True)
    manager = serializers.SerializerMethodField()
    company = serializers.SerializerMethodField()
    location_detail = LocationSerializer(source="location", read_only=True)
    customer_name = serializers.CharField(source="customer.full_name", read_only=True)
    request_reference = serializers.CharField(source="request.reference", read_only=True, default="")
    budget_total_label = serializers.SerializerMethodField()
    budget_spent_label = serializers.SerializerMethodField()
    budget_remaining_label = serializers.SerializerMethodField()
    metrics = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = (
            "id", "reference", "name", "slug", "kind", "kind_label", "status", "status_label",
            "health", "health_label", "health_notes", "description", "cover", "cover_url",
            "customer", "customer_name", "request_reference", "manager", "company",
            "location_detail", "location_text", "display_location", "address", "country",
            "latitude", "longitude", "physical_progress", "budget_total_xaf", "budget_spent_xaf",
            "budget_total_label", "budget_spent_label", "budget_remaining_label",
            "budget_used_percent", "is_over_budget", "is_late", "currency", "contract_signed",
            "planned_start", "planned_end", "actual_start", "actual_end", "next_visit_at",
            "customer_can_comment", "metrics", "created_at", "updated_at",
        )

    def get_manager(self, obj: Project) -> dict | None:
        if not obj.manager_id:
            return None
        return {
            "id": obj.manager.pk,
            "name": obj.manager.full_name,
            "phone": obj.manager.phone,
            "initials": obj.manager.initials,
        }

    def get_company(self, obj: Project) -> dict | None:
        if not obj.company_id:
            return None
        return {
            "id": obj.company.pk,
            "name": obj.company.name,
            "slug": obj.company.slug,
            "verified": obj.company.is_verified,
            "rating": float(obj.company.rating_average or 0),
        }

    def get_budget_total_label(self, obj: Project) -> str:
        return humanize_amount(obj.budget_total_xaf, obj.currency)

    def get_budget_spent_label(self, obj: Project) -> str:
        return humanize_amount(obj.budget_spent_xaf, obj.currency)

    def get_budget_remaining_label(self, obj: Project) -> str:
        return humanize_amount(obj.budget_remaining_xaf, obj.currency)

    def get_metrics(self, obj: Project) -> dict:
        cached = getattr(obj, "metrics_cache", None)
        if cached is not None:
            return cached
        from apps.projects.services import project_overview_payload

        return project_overview_payload(obj)["metrics"]


class ProjectDetailFullSerializer(ProjectDetailSerializer):
    """Version enrichie utilisée par l'écran de suivi de chantier."""

    phases = PhaseSerializer(many=True, read_only=True)
    members = ProjectMemberSerializer(many=True, read_only=True)
    budget_lines = BudgetLineSerializer(many=True, read_only=True)

    class Meta(ProjectDetailSerializer.Meta):
        fields = ProjectDetailSerializer.Meta.fields + ("phases", "members", "budget_lines")


class ProjectWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = (
            "name", "kind", "status", "health", "health_notes", "description", "manager",
            "company", "location", "location_text", "address", "country", "latitude",
            "longitude", "budget_total_xaf", "currency", "planned_start", "planned_end",
            "actual_start", "actual_end", "contract_signed", "cover", "customer_can_comment",
            "next_visit_at",
        )

    def validate(self, attrs):
        start = attrs.get("planned_start") or getattr(self.instance, "planned_start", None)
        end = attrs.get("planned_end") or getattr(self.instance, "planned_end", None)
        if start and end and end < start:
            raise serializers.ValidationError({
                "planned_end": "La date de livraison prévue doit être postérieure au démarrage."
            })
        if attrs.get("status") == ProjectStatus.COMPLETED and not (
            attrs.get("actual_end") or getattr(self.instance, "actual_end", None)
        ):
            attrs["actual_end"] = None  # laissé au service pour horodatage cohérent
        return attrs


class ProjectProgressSerializer(serializers.Serializer):
    progress = serializers.FloatField(min_value=0, max_value=100)
    note = serializers.CharField(required=False, allow_blank=True)
    notify_client = serializers.BooleanField(default=True)


class ProjectCommentSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=4000)

    def validate_message(self, value: str) -> str:
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Votre message est trop court.")
        return value.strip()
