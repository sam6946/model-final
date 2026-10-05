"""Routes des entreprises BTP."""
from django.urls import include, path

from apps.companies.views import (
    AdminCompanyViewSet,
    CompanyReviewViewSet,
    MyCompanyDocumentViewSet,
    MyCompanyView,
    PublicCompanyViewSet,
    SpecialtyListView,
)

urlpatterns = [
    path("catalog/specialties/", SpecialtyListView.as_view(), name="catalog-specialties"),
    path("companies/", PublicCompanyViewSet.as_view({"get": "list"}), name="public-companies"),
    path("companies/<slug:slug>/", PublicCompanyViewSet.as_view({"get": "retrieve"}), name="public-company-detail"),
    path("company/mine/", MyCompanyView.as_view(), name="my-company"),
    path(
        "company/documents/",
        include(
            [
                path("", MyCompanyDocumentViewSet.as_view({"get": "list", "post": "create"}), name="my-company-documents"),
                path("<int:pk>/", MyCompanyDocumentViewSet.as_view({"get": "retrieve", "delete": "destroy"}), name="my-company-document-detail"),
                path("<int:pk>/review/", MyCompanyDocumentViewSet.as_view({"post": "review"}), name="my-company-document-review"),
            ]
        ),
    ),
    path(
        "reviews/",
        include(
            [
                path("", CompanyReviewViewSet.as_view({"get": "list", "post": "create"}), name="company-reviews"),
                path("<int:pk>/moderate/", CompanyReviewViewSet.as_view({"post": "moderate"}), name="company-review-moderate"),
            ]
        ),
    ),
    path(
        "admin/companies/",
        include(
            [
                path("", AdminCompanyViewSet.as_view({"get": "list"}), name="admin-companies"),
                path("stats/", AdminCompanyViewSet.as_view({"get": "stats"}), name="admin-companies-stats"),
                path("<int:pk>/", AdminCompanyViewSet.as_view({"get": "retrieve"}), name="admin-company-detail"),
                path("<int:pk>/verify/", AdminCompanyViewSet.as_view({"post": "verify"}), name="admin-company-verify"),
                path("<int:pk>/feature/", AdminCompanyViewSet.as_view({"post": "feature"}), name="admin-company-feature"),
            ]
        ),
    ),
]
