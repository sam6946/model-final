"""API des preuves terrain (dont l'endpoint de synchronisation hors ligne)."""
from __future__ import annotations

from django.db.models import Count, Q
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from apps.construction.models import Phase
from apps.evidences.models import Evidence, EvidenceComment, EvidenceStatus
from apps.evidences.serializers import (
    EvidenceBulkSerializer,
    EvidenceCommentSerializer,
    EvidenceCreateSerializer,
    EvidenceReviewSerializer,
    EvidenceSerializer,
)
from apps.evidences.services import create_evidence, review_evidence, sync_offline_batch
from apps.projects.models import Project
from common.pagination import KemtaCursorPagination, KemtaPageNumberPagination
from common.permission_codes import Perm
from common.permissions import HasPermission
from common.throttling import PublicWriteThrottle


def _can_access_project(user, project: Project) -> bool:
    if project is None:
        return False
    if user.is_kemta_team or project.customer_id == user.pk or project.manager_id == user.pk:
        return True
    if project.members.filter(user=user, removed_at__isnull=True).exists():
        return True
    company = getattr(user, "primary_company", None)
    return bool(company and project.company_id == company.pk)


class ProjectEvidenceViewSet(ModelViewSet):
    """Preuves d'un projet : consultation client, dépôt terrain, validation."""

    serializer_class = EvidenceSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = KemtaCursorPagination
    filterset_fields = ["kind", "status", "phase"]
    ordering = ["-captured_at", "-created_at"]

    def get_queryset(self):
        queryset = (
            Evidence.objects.filter(project_id=self.kwargs["project_id"])
            .select_related("asset", "captured_by", "validated_by", "phase")
            .all()
        )
        project = Project.objects.filter(pk=self.kwargs["project_id"]).only("customer_id").first()
        user = self.request.user
        # Le client ne voit que les preuves validées (les brouillons restent internes).
        if project and project.customer_id == user.pk and not user.is_kemta_team:
            queryset = queryset.filter(status=EvidenceStatus.VALIDATED, is_visible_to_customer=True)
        return queryset

    def list(self, request, *args, **kwargs):
        project = Project.objects.filter(pk=self.kwargs["project_id"]).first()
        if project is None or not _can_access_project(request.user, project):
            return _error("not_found", "Ce chantier est introuvable ou vous n'y avez pas accès.", 404)
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        project = Project.objects.filter(pk=self.kwargs["project_id"]).first()
        if project is None or not _can_access_project(request.user, project):
            return _error("not_found", "Ce chantier est introuvable ou vous n'y avez pas accès.", 404)
        if not request.user.is_kemta_team and not _can_capture(request.user, project):
            return _error("forbidden", "Vous n'avez pas le droit de publier des preuves sur ce chantier.", 403)

        serializer = EvidenceCreateSerializer(data={**request.data, "project": project.pk})
        serializer.is_valid(raise_exception=True)
        evidence = create_evidence(data=dict(serializer.validated_data), actor=request.user)
        return Response(EvidenceSerializer(evidence).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="review")
    def review(self, request, project_id: int | None = None, pk: int | None = None):
        evidence = self.get_object()
        if not (request.user.is_kemta_team or _is_validator(request.user, evidence.project)):
            return _error("forbidden", "Seul un superviseur peut valider une preuve terrain.", 403)
        serializer = EvidenceReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        evidence = review_evidence(
            evidence=evidence,
            action=serializer.validated_data["action"],
            reviewer=request.user,
            comment=serializer.validated_data.get("comment", ""),
        )
        return Response(EvidenceSerializer(evidence).data)

    @action(detail=True, methods=["post"], url_path="comment")
    def comment(self, request, project_id: int | None = None, pk: int | None = None):
        evidence = self.get_object()
        body = (request.data.get("body") or "").strip()
        if len(body) < 2:
            return _error("invalid", "Écrivez votre commentaire avant d'envoyer.", 400)
        comment = EvidenceComment.objects.create(
            evidence=evidence,
            author=request.user,
            body=body,
            is_internal=bool(request.data.get("is_internal")) and request.user.is_kemta_team,
        )
        return Response(EvidenceCommentSerializer(comment).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="pending-count")
    def pending_count(self, request, project_id: int | None = None):
        counts = Evidence.objects.filter(project_id=self.kwargs["project_id"]).aggregate(
            pending=Count("id", filter=Q(status=EvidenceStatus.PENDING)),
            validated=Count("id", filter=Q(status=EvidenceStatus.VALIDATED)),
            rejected=Count("id", filter=Q(status=EvidenceStatus.REJECTED)),
        )
        return Response(counts)


class EvidenceSyncView(APIView):
    """Synchronisation d'un lot de preuves capturées hors ligne (PWA terrain).

    Idempotente : chaque preuve porte un ``client_uuid`` ; un envoi rejoué
    renvoie la preuve existante au lieu de la dupliquer.
    """

    permission_classes = [IsAuthenticated]
    throttle_classes = [PublicWriteThrottle]

    def post(self, request):
        serializer = EvidenceBulkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        items = serializer.validated_data["items"]

        allowed_items = []
        for item in items:
            data = dict(item)
            if data.get("project"):
                project = Project.objects.filter(pk=data["project"]).first()
                if project is None or not _can_access_project(request.user, project):
                    return _error("forbidden", "Vous n'avez pas accès à un des chantiers transmis.", 403)
            allowed_items.append(data)

        result = sync_offline_batch(items=allowed_items, actor=request.user)
        return Response(
            {
                "message": (
                    f"{result['created']} preuve(s) synchronisée(s)."
                    + (f" {result['replayed']} déjà présente(s) — aucun doublon créé." if result["replayed"] else "")
                ),
                **result,
            }
        )


class EvidenceReviewQueueView(APIView):
    """File de validation : ce que le superviseur doit arbitrer avant publication."""

    permission_classes = [IsAuthenticated, HasPermission(Perm.VALIDATE_EVIDENCE)]

    def get(self, request):
        queryset = (
            Evidence.objects.filter(status=EvidenceStatus.PENDING)
            .select_related("asset", "captured_by", "project", "phase")
            .order_by("created_at")
        )
        if request.query_params.get("project"):
            queryset = queryset.filter(project_id=request.query_params["project"])
        if request.query_params.get("suspect_location") in {"1", "true"}:
            queryset = queryset.filter(distance_to_site_m__gt=1500)

        paginator = KemtaPageNumberPagination()
        page = paginator.paginate_queryset(queryset, request)
        return paginator.get_paginated_response(EvidenceSerializer(page, many=True).data)


class EvidenceDetailView(APIView):
    """Accès à une preuve précise, avec contrôle d'accès."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk: int):
        evidence = Evidence.objects.select_related("asset", "project", "property", "phase").filter(pk=pk).first()
        if evidence is None:
            return _error("not_found", "Cette preuve est introuvable.", 404)
        if evidence.project and not _can_access_project(request.user, evidence.project):
            return _error("forbidden", "Vous n'avez pas accès à cette preuve.", 403)
        if (
            evidence.project
            and evidence.project.customer_id == request.user.pk
            and not request.user.is_kemta_team
            and evidence.status != EvidenceStatus.VALIDATED
        ):
            return _error("not_found", "Cette preuve est introuvable.", 404)
        return Response(EvidenceSerializer(evidence).data)

    def patch(self, request, pk: int):
        evidence = Evidence.objects.filter(pk=pk).first()
        if evidence is None:
            return _error("not_found", "Cette preuve est introuvable.", 404)
        if not (request.user.is_kemta_team or evidence.captured_by_id == request.user.pk):
            return _error("forbidden", "Vous ne pouvez pas modifier cette preuve.", 403)
        serializer = EvidenceSerializer(evidence, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


def _can_capture(user, project: Project) -> bool:
    if project.manager_id == user.pk:
        return True
    return project.members.filter(user=user, removed_at__isnull=True, can_capture_evidence=True).exists()


def _is_validator(user, project: Project | None) -> bool:
    if project is None:
        return user.is_kemta_team
    if project.manager_id == user.pk:
        return True
    return project.members.filter(user=user, removed_at__isnull=True, can_validate_evidence=True).exists()


def _error(code: str, message: str, http_status: int) -> Response:
    return Response({"error": {"code": code, "message": message}}, status=http_status)
