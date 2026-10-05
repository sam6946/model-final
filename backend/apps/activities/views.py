"""API des activités : fil client, fil projet, audit de sécurité."""
from __future__ import annotations

from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.activities.models import ActivityLog, AuditLog
from apps.activities.serializers import ActivityLogSerializer, AuditLogSerializer
from apps.projects.models import Project
from common.pagination import KemtaCursorPagination, KemtaPageNumberPagination
from common.permission_codes import Perm
from common.permissions import HasPermission


class ActivityFeedView(APIView):
    """Fil d'activité visible par l'utilisateur (ses projets, son entreprise)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        queryset = ActivityLog.objects.select_related("actor", "project").order_by("-created_at", "-id")

        if user.is_kemta_team:
            pass
        elif getattr(user, "primary_company", None):
            queryset = queryset.filter(
                Q(company=user.primary_company)
                | Q(project__company=user.primary_company)
                | Q(actor=user)
            )
        else:
            project_ids = list(
                Project.objects.filter(Q(customer=user) | Q(members__user=user))
                .values_list("id", flat=True)
                .distinct()
            )
            queryset = queryset.filter(
                Q(project_id__in=project_ids) | Q(actor=user), visibility__in=["CUSTOMER", "PUBLIC"]
            )

        if request.query_params.get("project"):
            queryset = queryset.filter(project_id=request.query_params["project"])
        if request.query_params.get("important") in {"1", "true"}:
            queryset = queryset.filter(is_important=True)

        paginator = KemtaCursorPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(ActivityLogSerializer(page, many=True).data)


class ProjectActivityView(APIView):
    """Journal complet d'un projet (accès contrôlé par l'adhésion au projet)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, project_id: int):
        project = Project.objects.filter(pk=project_id).first()
        if project is None:
            return Response(
                {"error": {"code": "not_found", "message": "Ce projet est introuvable."}},
                status=404,
            )
        if not request.user.is_kemta_team and project.customer_id != request.user.pk:
            if not project.members.filter(user=request.user).exists():
                return Response(
                    {"error": {"code": "forbidden", "message": "Vous n'avez pas accès à ce projet."}},
                    status=403,
                )
        queryset = project.activities.select_related("actor").order_by("-created_at", "-id")
        if project.customer_id == request.user.pk:
            queryset = queryset.filter(visibility__in=["CUSTOMER", "PUBLIC"])
        paginator = KemtaCursorPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(ActivityLogSerializer(page, many=True).data)


class AuditLogViewSet(ReadOnlyModelViewSet):
    """Audit de sécurité : réservé aux administrateurs KEMTA."""

    permission_classes = [IsAuthenticated, HasPermission(Perm.VIEW_AUTH_LOGS)]
    serializer_class = AuditLogSerializer
    pagination_class = KemtaPageNumberPagination
    filterset_fields = ["action", "user", "entity_type"]
    search_fields = ["description", "entity_id", "path", "user__phone"]
    ordering = ["-created_at"]
    queryset = AuditLog.objects.select_related("user").all()
