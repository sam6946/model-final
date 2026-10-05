"""Routes transverses : fichiers, référentiels publics, contenus éditoriaux."""
from django.urls import path

from common.views import (
    AssetCompleteView,
    AssetDetailView,
    DirectUploadView,
    LocationListView,
    PresignUploadView,
    PublicContentAPIView,
)

urlpatterns = [
    path("uploads/presign/", PresignUploadView.as_view(), name="uploads-presign"),
    path("uploads/direct/", DirectUploadView.as_view(), name="uploads-direct"),
    path("assets/<int:pk>/", AssetDetailView.as_view(), name="asset-detail"),
    path("assets/<int:pk>/complete/", AssetCompleteView.as_view(), name="asset-complete"),
    path("catalog/locations/", LocationListView.as_view(), name="catalog-locations"),
    path("catalog/public-content/", PublicContentAPIView.as_view(), name="catalog-public-content"),
]
