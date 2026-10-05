"""API des rapports : saisie terrain, validation, génération PDF client."""
from __future__ import annotations

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from apps.projects.models import Project
from apps.projects.views import _can_manage, _can_view
from apps.reports.models import DailyReport, PeriodicReport
from apps.reports.serializers import (
    DailyReportSerializer,
    PeriodicReportCreateSerializer,
    PeriodicReportSerializer,
)
from common.pagination import KemtaPageNumberPagination
from common.permission_codes import Perm
from common.permissions import HasPermission


class ProjectDailyReportViewSet(ModelViewSet):
    """Rapports journaliers d'un chantier."""

    serializer_class = DailyReportSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = KemtaPageNumberPagination
    filterset_fields = ["report_date", "weather", "is_visible_to_customer"]
    ordering = ["-report_date"]

    def get_queryset(self):
        queryset = DailyReport.objects.filter(project_id=self.kwargs["project_id"]).select_related("created_by", "project")
        project = Project.objects.filter(pk=self.kwargs["project_id"]).only("customer_id").first()
        if project and project.customer_id == self.request.user.pk and not self.request.user.is_kemta_team:
            queryset = queryset.filter(is_visible_to_customer=True, validated_at__isnull=False)
        return queryset

    def _project(self) -> Project | None:
        return Project.objects.filter(pk=self.kwargs["project_id"]).first()

    def list(self, request, *args, **kwargs):
        project = self._project()
        if project is None or not _can_view(request.user, project):
            return _error("not_found", "Ce chantier est introuvable ou vous n'y avez pas accès.", 404)
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        project = self._project()
        if project is None:
            return _error("not_found", "Ce chantier est introuvable.", 404)
        if not _can_manage(request.user, project):
            return _error("forbidden", "Seule l'équipe du chantier peut rédiger un rapport journalier.", 403)
        serializer = DailyReportSerializer(data={**request.data, "project": project.pk})
        serializer.is_valid(raise_exception=True)
        report = serializer.save(created_by=request.user, project=project)
        project.log_update(
            author=request.user,
            message=f"Rapport journalier du {report.report_date} enregistré.",
            update_type="REPORT",
            payload={"daily_report_id": report.pk, "weather": report.weather, "workers": report.total_present},
        )
        return Response(DailyReportSerializer(report).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        report = self.get_object()
        if not _can_manage(request.user, report.project):
            return _error("forbidden", "Vous ne pouvez pas modifier ce rapport.", 403)
        return super().update(request, *args, **kwargs)

    @action(detail=True, methods=["post"], url_path="validate")
    def validate_report(self, request, project_id: int | None = None, pk: int | None = None):
        report = self.get_object()
        if not (request.user.is_kemta_team or _can_manage(request.user, report.project)):
            return _error("forbidden", "Seul un superviseur valide un rapport journalier.", 403)
        report.validate_by(request.user, visible_to_customer=bool(request.data.get("visible", True)))
        report.project.log_update(
            author=request.user,
            message=f"Rapport du {report.report_date} validé et transmis au client.",
            update_type="REPORT",
            payload={"daily_report_id": report.pk},
        )
        return Response(DailyReportSerializer(report).data)


class ProjectPeriodicReportViewSet(ModelViewSet):
    """Rapports périodiques (hebdo/mensuel/fin de phase) et leur PDF."""

    serializer_class = PeriodicReportSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = KemtaPageNumberPagination
    filterset_fields = ["period", "status"]
    ordering = ["-period_end"]

    def get_queryset(self):
        queryset = PeriodicReport.objects.filter(project_id=self.kwargs["project_id"]).select_related("file", "project")
        project = Project.objects.filter(pk=self.kwargs["project_id"]).only("customer_id").first()
        if project and project.customer_id == self.request.user.pk and not self.request.user.is_kemta_team:
            queryset = queryset.filter(status__in=[PeriodicReport.Status.READY, PeriodicReport.Status.SENT])
        return queryset

    def _project(self) -> Project | None:
        return Project.objects.filter(pk=self.kwargs["project_id"]).first()

    def list(self, request, *args, **kwargs):
        project = self._project()
        if project is None or not _can_view(request.user, project):
            return _error("not_found", "Ce chantier est introuvable ou vous n'y avez pas accès.", 404)
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        project = self._project()
        if project is None:
            return _error("not_found", "Ce chantier est introuvable.", 404)
        if not _can_manage(request.user, project):
            return _error("forbidden", "Seule l'équipe KEMTA peut générer un rapport périodique.", 403)
        serializer = PeriodicReportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        report = PeriodicReport.objects.create(
            project=project,
            period=data["period"],
            title=data.get("title") or f"Rapport {data['period_start']} → {data['period_end']}",
            period_start=data["period_start"],
            period_end=data["period_end"],
            summary=data.get("summary", ""),
            highlights=data.get("highlights") or [],
            risks=data.get("risks") or [],
            next_steps=data.get("next_steps") or [],
            created_by=request.user,
        )
        report.build_snapshot()
        report.save(update_fields=["progress_snapshot"])

        from apps.reports.tasks import generate_periodic_report_pdf

        if settings_eager():
            generate_periodic_report_pdf.apply(kwargs={"report_id": report.pk}, throw=False)
        else:
            generate_periodic_report_pdf.delay(report_id=report.pk)
        report.refresh_from_db()
        return Response(PeriodicReportSerializer(report).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="regenerate")
    def regenerate(self, request, project_id: int | None = None, pk: int | None = None):
        report = self.get_object()
        if not _can_manage(request.user, report.project):
            return _error("forbidden", "Vous ne pouvez pas régénérer ce rapport.", 403)
        from apps.reports.tasks import generate_periodic_report_pdf

        report.build_snapshot()
        report.save(update_fields=["progress_snapshot"])
        if settings_eager():
            generate_periodic_report_pdf.apply(kwargs={"report_id": report.pk}, throw=False)
        else:
            generate_periodic_report_pdf.delay(report_id=report.pk)
        report.refresh_from_db()
        return Response(PeriodicReportSerializer(report).data)


def settings_eager() -> bool:
    from django.conf import settings

    return bool(settings.CELERY_TASK_ALWAYS_EAGER)


def _error(code: str, message: str, http_status: int) -> Response:
    return Response({"error": {"code": code, "message": message}}, status=http_status)
