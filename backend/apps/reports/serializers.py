"""Serializers des rapports journaliers et périodiques."""
from __future__ import annotations

from rest_framework import serializers

from apps.reports.models import DailyReport, PeriodicReport
from common.serializers import AssetSerializer


class DailyReportSerializer(serializers.ModelSerializer):
    weather_label = serializers.CharField(source="get_weather_display", read_only=True)
    author_name = serializers.CharField(source="created_by.full_name", read_only=True, default="")
    project_reference = serializers.CharField(source="project.reference", read_only=True)
    total_present = serializers.IntegerField(read_only=True)
    is_approved = serializers.BooleanField(read_only=True)

    class Meta:
        model = DailyReport
        fields = (
            "id", "project", "project_reference", "report_date", "weather", "weather_label",
            "workers_count", "supervisors_count", "total_present", "progress_percent",
            "works_done", "works_planned", "blockers", "decisions_needed", "materials_received",
            "equipment_used", "safety_notes", "hours_worked", "author_name", "validated_at",
            "is_approved", "is_visible_to_customer", "created_at", "updated_at",
        )
        read_only_fields = ("project", "validated_at", "created_at", "updated_at")

    def validate(self, attrs):
        report_date = attrs.get("report_date") or getattr(self.instance, "report_date", None)
        project = getattr(self.instance, "project", None) or attrs.get("project")
        if report_date and project:
            from django.utils import timezone

            if report_date > timezone.localdate():
                raise serializers.ValidationError({
                    "report_date": "Un rapport journalier ne peut pas porter une date future."
                })
            existing = DailyReport.objects.filter(project=project, report_date=report_date)
            if self.instance:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise serializers.ValidationError({
                    "report_date": "Un rapport existe déjà pour cette date. Modifiez-le plutôt que d'en créer un autre."
                })
        return attrs


class PeriodicReportSerializer(serializers.ModelSerializer):
    period_label = serializers.CharField(source="get_period_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    project_reference = serializers.CharField(source="project.reference", read_only=True)
    file_detail = AssetSerializer(source="file", read_only=True)

    class Meta:
        model = PeriodicReport
        fields = (
            "id", "project", "project_reference", "period", "period_label", "title",
            "period_start", "period_end", "summary", "progress_snapshot", "highlights",
            "risks", "next_steps", "financial_summary", "file", "file_detail", "status",
            "status_label", "generated_at", "sent_at", "created_at",
        )
        read_only_fields = ("progress_snapshot", "generated_at", "sent_at", "created_at")


class PeriodicReportCreateSerializer(serializers.Serializer):
    period = serializers.ChoiceField(choices=PeriodicReport.Period.choices, default=PeriodicReport.Period.WEEKLY)
    period_start = serializers.DateField()
    period_end = serializers.DateField()
    title = serializers.CharField(max_length=200, required=False, allow_blank=True)
    summary = serializers.CharField(required=False, allow_blank=True)
    highlights = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    risks = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    next_steps = serializers.ListField(child=serializers.CharField(), required=False, default=list)

    def validate(self, attrs):
        if attrs["period_end"] < attrs["period_start"]:
            raise serializers.ValidationError({"period_end": "La fin de période doit suivre le début."})
        return attrs
