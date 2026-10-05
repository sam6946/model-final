"""API des projets : suivi client, pilotage chantier, finances.

Deux familles d'accès, strictement séparées :

- **client** : ``/projects/mine/``, ``/projects/<id>/`` — un client ne voit que
  ses projets (client, membre de l'équipe projet, entreprise affectée) ;
- **back-office** : ``/admin/projects/...`` — équipe KEMTA, protégée par
  permissions explicites (``HasPermission``).
"""
from __future__ import annotations

from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from apps.activities.services import record_activity
from apps.activities.serializers import ActivityLogSerializer
from apps.construction.models import Phase
from apps.evidences.models import Evidence
from apps.evidences.serializers import EvidenceSerializer
from apps.projects.models import (
    BudgetLine,
    HealthStatus,
    Project,
    ProjectDocument,
    ProjectMember,
    ProjectStatus,
    ProjectUpdate,
    Task,
)
from apps.projects.serializers import (
    BudgetLineSerializer,
    PhaseSerializer,
    PhaseWriteSerializer,
    ProjectCommentSerializer,
    ProjectDetailFullSerializer,
    ProjectDetailSerializer,
    ProjectDocumentSerializer,
    ProjectListSerializer,
    ProjectMemberSerializer,
    ProjectProgressSerializer,
    ProjectUpdateSerializer,
    ProjectWriteSerializer,
    TaskSerializer,
)
from apps.projects.services import (
    create_task,
    portfolio_summary,
    project_overview_payload,
    update_progress,
)
from common.pagination import KemtaCursorPagination, KemtaPageNumberPagination
from common.permission_codes import Perm
from common.permissions import HasPermission


def _project_queryset():
    """Requête de base sans N+1 : tout ce qu'affiche un écran de projet."""
    return (
        Project.objects.select_related(
            "customer", "manager", "company", "location", "cover", "request"
        )
        .prefetch_related(
            "phases",
            "members__user",
            "budget_lines",
        )
    )


class MyProjectsView(APIView):
    """Projets du client connecté (ou desquels il est membre)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        queryset = _project_queryset().filter(Q(customer=user) | Q(members__user=user)).distinct()

        status_filter = request.query_params.get("status")
        if status_filter == "active":
            queryset = queryset.filter(
                status__in=[
                    ProjectStatus.DRAFT, ProjectStatus.PLANNING, ProjectStatus.IN_PROGRESS,
                    ProjectStatus.HANDOVER, ProjectStatus.ON_HOLD,
                ]
            )
        elif status_filter:
            queryset = queryset.filter(status=status_filter)
        if request.query_params.get("search"):
            search = request.query_params["search"]
            queryset = queryset.filter(Q(name__icontains=search) | Q(reference__icontains=search))

        queryset = queryset.order_by("-updated_at")
        paginator = KemtaPageNumberPagination()
        page = paginator.paginate_queryset(queryset, request)
        response = paginator.get_paginated_response(ProjectListSerializer(page, many=True).data)
        response.data["summary"] = portfolio_summary(user=user)
        return response


class ProjectScopedMixin:
    """Routes imbriquées (`project_id`) et routes simples (`pk`) partagent la même logique."""

    @property
    def project_pk(self) -> int | None:
        return self.kwargs.get("project_id") or self.kwargs.get("pk")


class ProjectDetailView(APIView):
    """Détail complet d'un projet : phases, équipe, budget, preuves récentes."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk: int):
        project = _project_queryset().filter(pk=pk).first()
        if project is None:
            return _not_found("projet")
        if not _can_view(request.user, project):
            return _forbidden()

        overview = project_overview_payload(project)
        data = ProjectDetailFullSerializer(project).data
        data["metrics"] = overview["metrics"]
        data["recent_evidences"] = EvidenceSerializer(
            overview["recent_evidences"], many=True, context={"request": request}
        ).data
        data["can_manage"] = _can_manage(request.user, project)
        data["can_view_finance"] = _can_view_finance(request.user, project)
        return Response(data)

    def patch(self, request, pk: int):
        project = _project_queryset().filter(pk=pk).first()
        if project is None:
            return _not_found("projet")
        if not _can_manage(request.user, project):
            return _forbidden()
        serializer = ProjectWriteSerializer(project, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        record_activity(
            verb="PROJECT_UPDATED",
            message=f"Fiche projet {project.reference} mise à jour",
            actor=request.user,
            project=project,
            entity_type="Project",
            entity_id=project.pk,
            visibility="TEAM",
        )
        return Response(ProjectDetailSerializer(project).data)

    def post(self, request, pk: int):
        """Commentaire client (ou note d'équipe) ajouté au fil du projet."""
        project = _project_queryset().filter(pk=pk).first()
        if project is None:
            return _not_found("projet")
        if not _can_view(request.user, project):
            return _forbidden()
        if not project.customer_can_comment and project.customer_id == request.user.pk:
            return Response(
                {
                    "error": {
                        "code": "comments_closed",
                        "message": "Les commentaires sont momentanément fermés sur ce chantier.",
                    }
                },
                status=status.HTTP_409_CONFLICT,
            )
        serializer = ProjectCommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        author = request.user
        update = ProjectUpdate.objects.create(
            project=project,
            author=author,
            update_type=ProjectUpdate.UpdateType.COMMENT
            if not author.is_kemta_team
            else ProjectUpdate.UpdateType.NOTE,
            message=serializer.validated_data["message"],
            visibility="CUSTOMER" if not author.is_kemta_team else "TEAM",
        )
        # La note d'équipe reste interne ; le commentaire client est notifié au manager.
        if author.is_kemta_team and project.customer_id:
            from apps.notifications.services import notify
            from common.constants import NotificationType

            notify(
                recipient=project.customer,
                notification_type=NotificationType.PROJECT,
                title=f"Message de l'équipe KEMTA — {project.name}",
                body=update.message[:280],
                action_url=f"/espace/projets/{project.pk}",
                action_label="Répondre",
                entity_type="Project",
                entity_id=project.pk,
                project=project,
                dedupe_key=f"project:{project.pk}:update:{update.pk}",
            )
        elif project.manager_id:
            from apps.notifications.services import notify
            from common.constants import NotificationType

            notify(
                recipient=project.manager,
                notification_type=NotificationType.PROJECT,
                title=f"Nouveau commentaire client — {project.reference}",
                body=update.message[:280],
                action_url=f"/admin/projets/{project.pk}",
                action_label="Voir le projet",
                entity_type="Project",
                entity_id=project.pk,
                project=project,
                dedupe_key=f"project:{project.pk}:client-comment:{update.pk}",
            )
        return Response(ProjectUpdateSerializer(update).data, status=status.HTTP_201_CREATED)


class ProjectTimelineView(APIView):
    """Fil chronologique du projet : mises à jour, preuves, rapports, finances."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk: int | None = None, project_id: int | None = None):
        project = Project.objects.filter(pk=pk or project_id).first()
        if project is None:
            return _not_found("projet")
        if not _can_view(request.user, project):
            return _forbidden()

        queryset = project.updates.select_related("author").order_by("-created_at", "-id")
        if project.customer_id == request.user.pk and not request.user.is_kemta_team:
            queryset = queryset.exclude(visibility="TEAM")
        paginator = KemtaCursorPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(ProjectUpdateSerializer(page, many=True).data)


class ProjectPhaseViewSet(ProjectScopedMixin, ModelViewSet):
    """Gestion des phases d'un projet (lecture client, écriture équipe)."""

    serializer_class = PhaseSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    filterset_fields = ["status"]

    def get_queryset(self):
        return Phase.objects.filter(project_id=self.project_pk).select_related("responsible")

    def get_serializer_class(self):
        if self.request.method in {"POST", "PUT", "PATCH"} and _is_manage_allowed(self.request, self.project_pk):
            return PhaseWriteSerializer
        return PhaseSerializer

    def _project(self) -> Project | None:
        return Project.objects.filter(pk=self.project_pk).first()

    def list(self, request, *args, **kwargs):
        project = self._project()
        if project is None:
            return _not_found("projet")
        if not _can_view(request.user, project):
            return _forbidden()
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        project = self._project()
        if project is None:
            return _not_found("projet")
        if not _can_manage(request.user, project):
            return _forbidden()
        serializer = PhaseWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phase = serializer.save(project=project)
        project.recalculate_progress()
        record_activity(
            verb="PHASE_UPDATED",
            message=f"Nouvelle étape « {phase.name} » sur {project.reference}",
            actor=request.user,
            project=project,
            entity_type="Phase",
            entity_id=phase.pk,
            visibility="CUSTOMER",
        )
        return Response(PhaseSerializer(phase).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        project = self._project()
        if project is None:
            return _not_found("projet")
        if not _can_manage(request.user, project):
            return _forbidden()
        phase = self.get_object()
        serializer = PhaseWriteSerializer(phase, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        phase = serializer.save()
        project.recalculate_progress()
        project.refresh_health()
        return Response(PhaseSerializer(phase).data)

    def destroy(self, request, *args, **kwargs):
        project = self._project()
        if project is None:
            return _not_found("projet")
        if not _can_manage(request.user, project):
            return _forbidden()
        phase = self.get_object()
        if phase.evidences.exists():
            return Response(
                {
                    "error": {
                        "code": "phase_has_evidence",
                        "message": "Cette étape contient des preuves terrain : archivez-la plutôt que de la supprimer.",
                    }
                },
                status=status.HTTP_409_CONFLICT,
            )
        phase.delete()
        project.recalculate_progress()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProjectTaskViewSet(ProjectScopedMixin, ModelViewSet):
    """Tâches d'un projet : création par l'équipe, avancement par le terrain."""

    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = KemtaPageNumberPagination
    filterset_fields = ["status", "priority", "assignee", "phase"]
    search_fields = ["title", "description"]
    ordering_fields = ["due_date", "priority", "created_at", "order"]
    ordering = ["order", "due_date"]

    def get_queryset(self):
        return (
            Task.objects.filter(project_id=self.project_pk)
            .select_related("assignee", "phase")
            .all()
        )

    def _project(self) -> Project | None:
        return Project.objects.filter(pk=self.project_pk).first()

    def list(self, request, *args, **kwargs):
        project = self._project()
        if project is None:
            return _not_found("projet")
        if not _can_view(request.user, project):
            return _forbidden()
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        project = self._project()
        if project is None:
            return _not_found("projet")
        if not _can_manage(request.user, project):
            return _forbidden()
        serializer = TaskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        phase = data.pop("phase", None)
        data.pop("project", None)
        if phase is not None:
            data["phase_id"] = phase.pk
        task = create_task(project=project, data=data, actor=request.user)
        return Response(TaskSerializer(task).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        project = self._project()
        if project is None:
            return _not_found("projet")
        task = self.get_object()
        # Le terrain peut faire avancer sa propre tâche sans droit de gestion global.
        can_edit_all = _can_manage(request.user, project)
        is_own_task = task.assignee_id == request.user.pk
        if not (can_edit_all or is_own_task):
            return _forbidden()
        if not can_edit_all:
            allowed = {"status", "progress_percent", "description"}
            if set(request.data.keys()) - allowed:
                return Response(
                    {
                        "error": {
                            "code": "restricted_fields",
                            "message": "Vous pouvez uniquement mettre à jour l'avancement de votre tâche.",
                        }
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
        serializer = TaskSerializer(task, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        previous_status = task.status
        task = serializer.save()
        if task.status != previous_status:
            if task.is_done:
                record_activity(
                    verb="TASK_COMPLETED",
                    message=f"Tâche terminée : {task.title}",
                    actor=request.user,
                    project=project,
                    entity_type="Task",
                    entity_id=task.pk,
                    visibility="CUSTOMER",
                )
            if task.phase_id:
                task.phase.recalculate_project_progress()
        return Response(TaskSerializer(task).data)

    def destroy(self, request, *args, **kwargs):
        project = self._project()
        if project is None:
            return _not_found("projet")
        if not _can_manage(request.user, project):
            return _forbidden()
        return super().destroy(request, *args, **kwargs)


class ProjectBudgetViewSet(ProjectScopedMixin, ModelViewSet):
    """Lignes budgétaires (accès finance requis)."""

    serializer_class = BudgetLineSerializer
    permission_classes = [IsAuthenticated, HasPermission(Perm.VIEW_FINANCE)]
    pagination_class = None
    filterset_fields = ["category", "phase"]

    def get_queryset(self):
        return BudgetLine.objects.filter(project_id=self.project_pk).select_related("phase")

    def _guard(self, request) -> Response | None:
        project = Project.objects.filter(pk=self.project_pk).first()
        if project is None:
            return _not_found("projet")
        if not _can_view_finance(request.user, project):
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": "Vous n'avez pas accès aux informations financières de ce projet.",
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        if request.method not in {"GET", "HEAD", "OPTIONS"} and not _can_manage(request.user, project):
            return _forbidden()
        return None

    def list(self, request, *args, **kwargs):
        if (blocked := self._guard(request)) is not None:
            return blocked
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        if (blocked := self._guard(request)) is not None:
            return blocked
        serializer = BudgetLineSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        line = serializer.save(project_id=self.project_pk, updated_by=request.user)
        return Response(BudgetLineSerializer(line).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        if (blocked := self._guard(request)) is not None:
            return blocked
        line = self.get_object()
        serializer = BudgetLineSerializer(line, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(updated_by=request.user)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        if (blocked := self._guard(request)) is not None:
            return blocked
        return super().destroy(request, *args, **kwargs)

class ProjectBudgetSummaryView(APIView):
    """Synthèse budgétaire : par catégorie et globale (une seule agrégation SQL)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk: int | None = None, project_id: int | None = None):
        project = Project.objects.filter(pk=pk or project_id).first()
        if project is None:
            return _not_found("projet")
        if not _can_view_finance(request.user, project):
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": "Vous n'avez pas accès aux informations financières de ce projet.",
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        by_category = (
            BudgetLine.objects.filter(project=project)
            .values("category")
            .annotate(
                planned=Sum("planned_xaf"),
                committed=Sum("committed_xaf"),
                spent=Sum("spent_xaf"),
                lines=Count("id"),
            )
            .order_by("-planned")
        )
        totals = BudgetLine.objects.filter(project=project).aggregate(
            planned=Sum("planned_xaf"), committed=Sum("committed_xaf"), spent=Sum("spent_xaf")
        )
        labels = dict(BudgetLine.Category.choices)
        return Response(
            {
                "project_budget_xaf": float(project.budget_total_xaf or 0),
                "project_spent_xaf": float(project.budget_spent_xaf or 0),
                "budget_used_percent": project.budget_used_percent,
                "budget_remaining_xaf": float(project.budget_remaining_xaf),
                "is_over_budget": project.is_over_budget,
                "totals": {key: float(value or 0) for key, value in totals.items()},
                "by_category": [
                    {
                        "category": row["category"],
                        "label": labels.get(row["category"], row["category"]),
                        "planned_xaf": float(row["planned"] or 0),
                        "committed_xaf": float(row["committed"] or 0),
                        "spent_xaf": float(row["spent"] or 0),
                        "lines": row["lines"],
                    }
                    for row in by_category
                ],
            }
        )


class ProjectMemberViewSet(ProjectScopedMixin, ModelViewSet):
    """Équipe projet : ajout de membres et de techniciens terrain."""

    serializer_class = ProjectMemberSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return ProjectMember.objects.filter(project_id=self.project_pk, removed_at__isnull=True).select_related("user")

    def create(self, request, *args, **kwargs):
        project = Project.objects.filter(pk=self.project_pk).first()
        if project is None:
            return _not_found("projet")
        if not _can_manage(request.user, project):
            return _forbidden()
        serializer = ProjectMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        existing = ProjectMember.objects.filter(project=project, user=user).first()
        if existing and existing.removed_at is None:
            return Response(
                {"error": {"code": "already_member", "message": "Cette personne fait déjà partie du projet."}},
                status=status.HTTP_409_CONFLICT,
            )
        if existing:
            existing.removed_at = None
            existing.role = serializer.validated_data.get("role", existing.role)
            existing.save(update_fields=["removed_at", "role"])
            member = existing
        else:
            member = serializer.save(project=project, added_by=request.user)
        record_activity(
            verb="MEMBER_ADDED",
            message=f"{member.user.full_name} ajouté au projet {project.reference}",
            actor=request.user,
            project=project,
            entity_type="ProjectMember",
            entity_id=member.pk,
            visibility="TEAM",
        )
        # La personne ajoutée doit savoir qu'elle a accès au chantier.
        from apps.notifications.services import notify
        from common.constants import NotificationType

        notify(
            recipient=member.user,
            notification_type=NotificationType.PROJECT,
            title="Vous avez accès à un chantier KEMTA",
            body=f"Projet {project.reference} — {project.name}.",
            action_url=f"/admin/projets/{project.pk}" if member.user.is_kemta_team else f"/espace/projets/{project.pk}",
            action_label="Ouvrir le chantier",
            entity_type="Project",
            entity_id=project.pk,
            project=project,
            dedupe_key=f"project:{project.pk}:member:{member.user_id}",
        )
        return Response(ProjectMemberSerializer(member).data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        project = Project.objects.filter(pk=self.project_pk).first()
        if project is None:
            return _not_found("projet")
        if not _can_manage(request.user, project):
            return _forbidden()
        member = self.get_object()
        if member.role == ProjectMember.MemberRole.MANAGER and member.user_id == project.manager_id:
            return Response(
                {
                    "error": {
                        "code": "last_manager",
                        "message": "Désignez d'abord un autre chargé de suivi avant de retirer celui-ci.",
                    }
                },
                status=status.HTTP_409_CONFLICT,
            )
        member.removed_at = timezone.now()
        member.save(update_fields=["removed_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProjectDocumentViewSet(ProjectScopedMixin, ModelViewSet):
    """Documents partagés du projet (plans, devis, procès-verbaux)."""

    serializer_class = ProjectDocumentSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    filterset_fields = ["kind"]

    def get_queryset(self):
        queryset = ProjectDocument.objects.filter(project_id=self.project_pk).select_related("asset", "uploaded_by")
        project = Project.objects.filter(pk=self.project_pk).first()
        if project and project.customer_id == self.request.user.pk and not self.request.user.is_kemta_team:
            queryset = queryset.filter(visible_to_customer=True)
        return queryset

    def list(self, request, *args, **kwargs):
        project = Project.objects.filter(pk=self.project_pk).first()
        if project is None:
            return _not_found("projet")
        if not _can_view(request.user, project):
            return _forbidden()
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        project = Project.objects.filter(pk=self.project_pk).first()
        if project is None:
            return _not_found("projet")
        if not _can_manage(request.user, project):
            return _forbidden()
        serializer = ProjectDocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document = serializer.save(project=project, uploaded_by=request.user)
        record_activity(
            verb="DOCUMENT_UPLOADED",
            message=f"Document « {document.title} » ajouté au projet {project.reference}",
            actor=request.user,
            project=project,
            entity_type="ProjectDocument",
            entity_id=document.pk,
            visibility="CUSTOMER" if document.visible_to_customer else "TEAM",
        )
        return Response(ProjectDocumentSerializer(document).data, status=status.HTTP_201_CREATED)


class ProjectProgressView(APIView):
    """Mise à jour de l'avancement global (équipe projet)."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk: int | None = None, project_id: int | None = None):
        project = Project.objects.filter(pk=pk or project_id).first()
        if project is None:
            return _not_found("projet")
        if not _can_manage(request.user, project):
            return _forbidden()
        serializer = ProjectProgressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = update_progress(
            project=project,
            progress=serializer.validated_data["progress"],
            actor=request.user,
            note=serializer.validated_data.get("note", ""),
            notify_client=serializer.validated_data.get("notify_client", True),
        )
        return Response(ProjectDetailSerializer(project).data)


class AdminProjectViewSet(ModelViewSet):
    """Back-office : pilotage global des projets et des chantiers."""

    permission_classes = [IsAuthenticated, HasPermission(Perm.MANAGE_PROJECT)]
    pagination_class = KemtaPageNumberPagination
    filterset_fields = ["status", "health", "kind", "manager", "company", "customer"]
    search_fields = ["reference", "name", "location_text", "customer__first_name", "customer__last_name"]
    ordering_fields = ["created_at", "updated_at", "physical_progress", "planned_end"]
    ordering = ["-updated_at"]

    def get_queryset(self):
        queryset = _project_queryset()
        if self.request.query_params.get("at_risk") in {"1", "true"}:
            queryset = queryset.filter(health__in=[HealthStatus.AT_RISK, HealthStatus.WATCH])
        if self.request.query_params.get("late") in {"1", "true"}:
            queryset = queryset.filter(
                planned_end__lt=timezone.localdate(),
                status__in=[ProjectStatus.PLANNING, ProjectStatus.IN_PROGRESS, ProjectStatus.HANDOVER,
                            ProjectStatus.ON_HOLD],
            )
        return queryset

    def get_serializer_class(self):
        if self.action in {"update", "partial_update", "create"}:
            return ProjectWriteSerializer
        if self.action == "retrieve":
            return ProjectDetailFullSerializer
        return ProjectListSerializer

    @action(detail=False, methods=["get"], url_path="stats")
    def stats(self, request):
        """Indicateurs opérationnels consolidés (une seule requête)."""
        aggregates = Project.objects.aggregate(
            total=Count("id"),
            active=Count("id", filter=Q(status__in=[ProjectStatus.PLANNING, ProjectStatus.IN_PROGRESS,
                                                    ProjectStatus.HANDOVER, ProjectStatus.ON_HOLD])),
            completed=Count("id", filter=Q(status=ProjectStatus.COMPLETED)),
            at_risk=Count("id", filter=Q(health=HealthStatus.AT_RISK)),
            watch=Count("id", filter=Q(health=HealthStatus.WATCH)),
            budget_total=Sum("budget_total_xaf"),
            budget_spent=Sum("budget_spent_xaf"),
        )
        by_status = list(Project.objects.values("status").annotate(total=Count("id")).order_by("-total"))
        return Response(
            {
                **{key: (value or 0) for key, value in aggregates.items()},
                "by_status": by_status,
                "pending_evidences": Evidence.objects.filter(status="PENDING").count(),
            }
        )

    @action(detail=True, methods=["get"], url_path="activity")
    def activity(self, request, pk=None):
        project = self.get_object()
        queryset = project.activities.select_related("actor").order_by("-created_at")[:50]
        return Response(ActivityLogSerializer(queryset, many=True).data)


def _can_view(user, project: Project) -> bool:
    if user.is_kemta_team:
        return True
    if project.customer_id == user.pk or project.manager_id == user.pk:
        return True
    if project.members.filter(user=user, removed_at__isnull=True).exists():
        return True
    company = getattr(user, "primary_company", None)
    return bool(company and project.company_id == company.pk)


def _can_manage(user, project: Project) -> bool:
    if user.is_kemta_team:
        return True
    if project.manager_id == user.pk:
        return True
    if project.members.filter(user=user, removed_at__isnull=True,
                              role__in=[ProjectMember.MemberRole.MANAGER, ProjectMember.MemberRole.SUPERVISOR]).exists():
        return True
    company = getattr(user, "primary_company", None)
    return bool(company and project.company_id == company.pk)


def _can_view_finance(user, project: Project) -> bool:
    """Transparence financière : le client et son équipe voient l'argent qui est dépensé."""
    if user.is_kemta_team or project.customer_id == user.pk or project.manager_id == user.pk:
        return True
    if project.members.filter(user=user, removed_at__isnull=True, can_view_finance=True).exists():
        return True
    from common.permissions import get_user_permissions

    return Perm.VIEW_FINANCE in get_user_permissions(user)


def _is_manage_allowed(request, project_id: int) -> bool:
    project = Project.objects.filter(pk=project_id).first()
    return bool(project and _can_manage(request.user, project))


def _not_found(label: str) -> Response:
    return Response(
        {"error": {"code": "not_found", "message": f"Ce {label} est introuvable ou vous n'y avez pas accès."}},
        status=status.HTTP_404_NOT_FOUND,
    )


def _forbidden() -> Response:
    return Response(
        {
            "error": {
                "code": "forbidden",
                "message": "Vous n'avez pas l'autorisation d'effectuer cette action sur ce projet.",
            }
        },
        status=status.HTTP_403_FORBIDDEN,
    )
