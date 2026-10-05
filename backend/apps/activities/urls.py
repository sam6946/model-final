"""Routes du fil d'activité et de l'audit."""
from django.urls import include, path

from apps.activities.views import ActivityFeedView, AuditLogViewSet, ProjectActivityView

urlpatterns = [
    path("activities/", ActivityFeedView.as_view(), name="activities-feed"),
    path("projects/<int:project_id>/activity/", ProjectActivityView.as_view(), name="project-activity"),
    path(
        "admin/audit-logs/",
        include(
            [
                path("", AuditLogViewSet.as_view({"get": "list"}), name="admin-audit-logs"),
                path("<int:pk>/", AuditLogViewSet.as_view({"get": "retrieve"}), name="admin-audit-log-detail"),
            ]
        ),
    ),
]
