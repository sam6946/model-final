"""Routes des rapports de chantier."""
from django.urls import include, path

from apps.reports.views import ProjectDailyReportViewSet, ProjectPeriodicReportViewSet

urlpatterns = [
    path(
        "projects/<int:project_id>/reports/daily/",
        include(
            [
                path("", ProjectDailyReportViewSet.as_view({"get": "list", "post": "create"}), name="project-daily-reports"),
                path("<int:pk>/", ProjectDailyReportViewSet.as_view({
                    "get": "retrieve", "patch": "partial_update",
                }), name="project-daily-report-detail"),
                path("<int:pk>/validate/", ProjectDailyReportViewSet.as_view({"post": "validate_report"}), name="project-daily-report-validate"),
            ]
        ),
    ),
    path(
        "projects/<int:project_id>/reports/periodic/",
        include(
            [
                path("", ProjectPeriodicReportViewSet.as_view({"get": "list", "post": "create"}), name="project-periodic-reports"),
                path("<int:pk>/", ProjectPeriodicReportViewSet.as_view({"get": "retrieve"}), name="project-periodic-report-detail"),
                path("<int:pk>/regenerate/", ProjectPeriodicReportViewSet.as_view({"post": "regenerate"}), name="project-periodic-report-regenerate"),
            ]
        ),
    ),
]
