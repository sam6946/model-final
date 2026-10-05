"""Routes des projets, phases, tâches, budget, documents et preuves."""
from django.urls import include, path

from apps.projects.views import (
    AdminProjectViewSet,
    MyProjectsView,
    ProjectBudgetSummaryView,
    ProjectBudgetViewSet,
    ProjectDetailView,
    ProjectDocumentViewSet,
    ProjectMemberViewSet,
    ProjectPhaseViewSet,
    ProjectProgressView,
    ProjectTaskViewSet,
    ProjectTimelineView,
)

project_nested = [
    path("phases/", ProjectPhaseViewSet.as_view({"get": "list", "post": "create"}), name="project-phases"),
    path(
        "phases/<int:pk>/",
        ProjectPhaseViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}),
        name="project-phase-detail",
    ),
    path("tasks/", ProjectTaskViewSet.as_view({"get": "list", "post": "create"}), name="project-tasks"),
    path(
        "tasks/<int:pk>/",
        ProjectTaskViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}),
        name="project-task-detail",
    ),
    path("budget-lines/", ProjectBudgetViewSet.as_view({"get": "list", "post": "create"}), name="project-budget-lines"),
    path(
        "budget-lines/<int:pk>/",
        ProjectBudgetViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}),
        name="project-budget-line-detail",
    ),
    path("budget-summary/", ProjectBudgetSummaryView.as_view(), name="project-budget-summary"),
    path("members/", ProjectMemberViewSet.as_view({"get": "list", "post": "create"}), name="project-members"),
    path("members/<int:pk>/", ProjectMemberViewSet.as_view({"delete": "destroy"}), name="project-member-detail"),
    path("documents/", ProjectDocumentViewSet.as_view({"get": "list", "post": "create"}), name="project-documents"),
    path("documents/<int:pk>/", ProjectDocumentViewSet.as_view({"get": "retrieve"}), name="project-document-detail"),
    path("timeline/", ProjectTimelineView.as_view(), name="project-timeline"),
    path("progress/", ProjectProgressView.as_view(), name="project-progress"),
]

urlpatterns = [
    path("projects/mine/", MyProjectsView.as_view(), name="my-projects"),
    path("projects/<int:project_id>/", include(project_nested)),
    path("projects/<int:pk>/", ProjectDetailView.as_view(), name="project-detail"),
    path(
        "admin/projects/",
        include(
            [
                path("", AdminProjectViewSet.as_view({"get": "list", "post": "create"}), name="admin-projects"),
                path("stats/", AdminProjectViewSet.as_view({"get": "stats"}), name="admin-projects-stats"),
                path("<int:pk>/", AdminProjectViewSet.as_view({
                    "get": "retrieve", "patch": "partial_update", "put": "update",
                }), name="admin-project-detail"),
                path("<int:pk>/activity/", AdminProjectViewSet.as_view({"get": "activity"}), name="admin-project-activity"),
            ]
        ),
    ),
]
