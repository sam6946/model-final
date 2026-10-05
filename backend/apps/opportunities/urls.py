"""Routes des opportunités BTP."""
from django.urls import include, path

from apps.opportunities.views import PublicOpportunityViewSet
from apps.opportunities.views_admin import AdminOpportunityViewSet

urlpatterns = [
    path("opportunities/", PublicOpportunityViewSet.as_view({"get": "list"}), name="public-opportunities"),
    path("opportunities/stats/", PublicOpportunityViewSet.as_view({"get": "stats"}), name="public-opportunities-stats"),
    path("opportunities/<slug:slug>/", PublicOpportunityViewSet.as_view({"get": "retrieve"}), name="public-opportunity-detail"),
    path(
        "admin/opportunities/",
        include(
            [
                path("", AdminOpportunityViewSet.as_view({"get": "list", "post": "create"}), name="admin-opportunities"),
                path("stats/", AdminOpportunityViewSet.as_view({"get": "stats"}), name="admin-opportunities-stats"),
                path("<int:pk>/", AdminOpportunityViewSet.as_view({
                    "get": "retrieve", "patch": "partial_update", "put": "update", "delete": "destroy",
                }), name="admin-opportunity-detail"),
                path("<int:pk>/publish/", AdminOpportunityViewSet.as_view({"post": "publish"}), name="admin-opportunity-publish"),
                path("<int:pk>/applications/", AdminOpportunityViewSet.as_view({"get": "applications"}), name="admin-opportunity-applications"),
            ]
        ),
    ),
]
