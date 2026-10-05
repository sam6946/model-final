"""Routes des candidatures BTP."""
from django.urls import include, path

from apps.applications.views import (
    AdminApplicationViewSet,
    MyApplicationViewSet,
    OpportunityApplyView,
)
from apps.btp_catalog.views import PublicRealizationViewSet

urlpatterns = [
    path("opportunities/<slug:slug>/apply/", OpportunityApplyView.as_view(), name="opportunity-apply"),
    path(
        "applications/mine/",
        include(
            [
                path("", MyApplicationViewSet.as_view({"get": "list"}), name="my-applications"),
                path("stats/", MyApplicationViewSet.as_view({"get": "stats"}), name="my-applications-stats"),
                path("<int:pk>/", MyApplicationViewSet.as_view({"get": "retrieve"}), name="my-application-detail"),
                path("<int:pk>/withdraw/", MyApplicationViewSet.as_view({"post": "withdraw"}), name="my-application-withdraw"),
            ]
        ),
    ),
    path(
        "admin/applications/",
        include(
            [
                path("", AdminApplicationViewSet.as_view({"get": "list"}), name="admin-applications"),
                path("stats/", AdminApplicationViewSet.as_view({"get": "stats"}), name="admin-applications-stats"),
                path("<int:pk>/", AdminApplicationViewSet.as_view({
                    "get": "retrieve", "patch": "partial_update", "put": "update",
                }), name="admin-application-detail"),
            ]
        ),
    ),
]
