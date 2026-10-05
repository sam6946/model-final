"""Routes des preuves terrain."""
from django.urls import include, path

from apps.evidences.views import (
    EvidenceDetailView,
    EvidenceReviewQueueView,
    EvidenceSyncView,
    ProjectEvidenceViewSet,
)

urlpatterns = [
    path(
        "projects/<int:project_id>/evidences/",
        include(
            [
                path("", ProjectEvidenceViewSet.as_view({"get": "list", "post": "create"}), name="project-evidences"),
                path("pending-count/", ProjectEvidenceViewSet.as_view({"get": "pending_count"}), name="project-evidences-pending"),
                path("<int:pk>/", ProjectEvidenceViewSet.as_view({"get": "retrieve"}), name="project-evidence-detail"),
                path("<int:pk>/review/", ProjectEvidenceViewSet.as_view({"post": "review"}), name="project-evidence-review"),
                path("<int:pk>/comment/", ProjectEvidenceViewSet.as_view({"post": "comment"}), name="project-evidence-comment"),
            ]
        ),
    ),
    path("evidences/sync/", EvidenceSyncView.as_view(), name="evidences-sync"),
    path("evidences/review-queue/", EvidenceReviewQueueView.as_view(), name="evidences-review-queue"),
    path("evidences/<int:pk>/", EvidenceDetailView.as_view(), name="evidence-detail"),
]
