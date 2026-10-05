"""Routes de l'entretien immobilier."""
from django.urls import include, path

from apps.maintenance.views import (
    MaintenanceContractViewSet,
    MaintenanceIssueViewSet,
    MaintenanceOverviewView,
    MaintenanceServiceCatalogView,
    MaintenanceVisitViewSet,
)

urlpatterns = [
    path("maintenance/services/", MaintenanceServiceCatalogView.as_view(), name="maintenance-services"),
    path("maintenance/overview/", MaintenanceOverviewView.as_view(), name="maintenance-overview"),
    path(
        "maintenance/contracts/",
        include(
            [
                path("", MaintenanceContractViewSet.as_view({"get": "list", "post": "create"}), name="maintenance-contracts"),
                path("<int:pk>/", MaintenanceContractViewSet.as_view({
                    "get": "retrieve", "patch": "partial_update",
                }), name="maintenance-contract-detail"),
                path("<int:pk>/generate-visits/", MaintenanceContractViewSet.as_view({"post": "generate_visits"}), name="maintenance-contract-generate"),
                path("<int:pk>/pause/", MaintenanceContractViewSet.as_view({"post": "pause"}), name="maintenance-contract-pause"),
            ]
        ),
    ),
    path(
        "maintenance/visits/",
        include(
            [
                path("", MaintenanceVisitViewSet.as_view({"get": "list"}), name="maintenance-visits"),
                path("calendar/", MaintenanceVisitViewSet.as_view({"get": "calendar"}), name="maintenance-visits-calendar"),
                path("<int:pk>/", MaintenanceVisitViewSet.as_view({
                    "get": "retrieve", "patch": "partial_update",
                }), name="maintenance-visit-detail"),
                path("<int:pk>/complete/", MaintenanceVisitViewSet.as_view({"post": "complete"}), name="maintenance-visit-complete"),
            ]
        ),
    ),
    path(
        "maintenance/issues/",
        include(
            [
                path("", MaintenanceIssueViewSet.as_view({"get": "list", "post": "create"}), name="maintenance-issues"),
                path("<int:pk>/", MaintenanceIssueViewSet.as_view({"get": "retrieve"}), name="maintenance-issue-detail"),
                path("<int:pk>/status/", MaintenanceIssueViewSet.as_view({"post": "set_status"}), name="maintenance-issue-status"),
            ]
        ),
    ),
]
