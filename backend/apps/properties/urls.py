"""Routes des propriétés."""
from django.urls import include, path

from apps.properties.views import AdminPropertyViewSet, MyPropertyViewSet

urlpatterns = [
    path(
        "properties/",
        include(
            [
                path("", MyPropertyViewSet.as_view({"get": "list", "post": "create"}), name="properties"),
                path("stats/", MyPropertyViewSet.as_view({"get": "stats"}), name="properties-stats"),
                path("<int:pk>/", MyPropertyViewSet.as_view({
                    "get": "retrieve", "patch": "partial_update", "put": "update", "delete": "destroy",
                }), name="property-detail"),
                path("<int:pk>/photos/", MyPropertyViewSet.as_view({"post": "add_photo"}), name="property-photos"),
                path("<int:pk>/register-visit/", MyPropertyViewSet.as_view({"post": "register_visit"}), name="property-register-visit"),
            ]
        ),
    ),
    path(
        "admin/properties/",
        include(
            [
                path("", AdminPropertyViewSet.as_view({"get": "list", "post": "create"}), name="admin-properties"),
                path("<int:pk>/", AdminPropertyViewSet.as_view({
                    "get": "retrieve", "patch": "partial_update",
                }), name="admin-property-detail"),
            ]
        ),
    ),
]
