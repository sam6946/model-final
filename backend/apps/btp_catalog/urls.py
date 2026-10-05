"""Routes du catalogue de réalisations."""
from django.urls import include, path

from apps.btp_catalog.views import (
    AdminRealizationViewSet,
    MyRealizationViewSet,
    PublicRealizationViewSet,
)

urlpatterns = [
    path("catalog/realizations/", PublicRealizationViewSet.as_view({"get": "list"}), name="public-realizations"),
    path("catalog/realizations/filters/", PublicRealizationViewSet.as_view({"get": "filters"}), name="public-realizations-filters"),
    path("catalog/realizations/<slug:slug>/", PublicRealizationViewSet.as_view({"get": "retrieve"}), name="public-realization-detail"),
    path(
        "company/realizations/",
        include(
            [
                path("", MyRealizationViewSet.as_view({"get": "list", "post": "create"}), name="my-realizations"),
                path("<int:pk>/", MyRealizationViewSet.as_view({
                    "get": "retrieve", "patch": "partial_update", "delete": "destroy",
                }), name="my-realization-detail"),
                path("<int:pk>/media/", MyRealizationViewSet.as_view({"post": "add_media"}), name="my-realization-media"),
            ]
        ),
    ),
    path(
        "admin/realizations/",
        include(
            [
                path("", AdminRealizationViewSet.as_view({"get": "list"}), name="admin-realizations"),
                path("<int:pk>/decision/", AdminRealizationViewSet.as_view({"post": "decision"}), name="admin-realization-decision"),
            ]
        ),
    ),
]
