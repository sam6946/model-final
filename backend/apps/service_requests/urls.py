"""Routes des demandes de service (formulaires multi-étapes du site)."""
from django.urls import include, path

from apps.service_requests.views import (
    AdminServiceRequestViewSet,
    MyServiceRequestDetailView,
    MyServiceRequestsView,
    ServiceCatalogListView,
    ServiceRequestCreateView,
)

urlpatterns = [
    path("services/", ServiceCatalogListView.as_view(), name="service-catalog"),
    path("requests/", ServiceRequestCreateView.as_view(), name="service-request-create"),
    path("requests/mine/", MyServiceRequestsView.as_view(), name="my-service-requests"),
    path("requests/mine/<str:reference>/", MyServiceRequestDetailView.as_view(), name="my-service-request-detail"),
    path(
        "admin/requests/",
        include(
            [
                path("", AdminServiceRequestViewSet.as_view({"get": "list"}), name="admin-requests"),
                path("stats/", AdminServiceRequestViewSet.as_view({"get": "stats"}), name="admin-requests-stats"),
                path("<int:pk>/", AdminServiceRequestViewSet.as_view({
                    "get": "retrieve", "patch": "partial_update",
                }), name="admin-request-detail"),
                path("<int:pk>/assign/", AdminServiceRequestViewSet.as_view({"post": "assign"}), name="admin-request-assign"),
                path("<int:pk>/status/", AdminServiceRequestViewSet.as_view({"post": "set_status"}), name="admin-request-status"),
                path("<int:pk>/convert/", AdminServiceRequestViewSet.as_view({"post": "convert"}), name="admin-request-convert"),
            ]
        ),
    ),
]
