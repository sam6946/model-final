"""Routes des abonnements."""
from django.urls import include, path

from apps.subscriptions.views import AdminPlanViewSet, MySubscriptionView, PlanListView

urlpatterns = [
    path("plans/", PlanListView.as_view(), name="plans"),
    path("subscriptions/mine/", MySubscriptionView.as_view(), name="my-subscription"),
    path(
        "admin/plans/",
        include(
            [
                path("", AdminPlanViewSet.as_view({"get": "list", "post": "create"}), name="admin-plans"),
                path("stats/", AdminPlanViewSet.as_view({"get": "stats"}), name="admin-plans-stats"),
                path("<int:pk>/", AdminPlanViewSet.as_view({
                    "get": "retrieve", "patch": "partial_update", "put": "update",
                }), name="admin-plan-detail"),
            ]
        ),
    ),
]
