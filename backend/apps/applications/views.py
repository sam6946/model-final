"""API des candidatures : dépôt par l'entreprise, instruction par KEMTA."""
from __future__ import annotations

from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from apps.applications.models import Application, ApplicationStatus
from apps.applications.serializers import (
    ApplicationCreateSerializer,
    ApplicationDetailSerializer,
    ApplicationListSerializer,
    ApplicationReviewSerializer,
)
from apps.applications.services import review_application, submit_application, withdraw_application
from apps.btp_catalog.models import Realization
from apps.companies.models import Company, CompanyMember
from apps.opportunities.models import Opportunity, OpportunityStatus
from common.pagination import KemtaPageNumberPagination
from common.permission_codes import Perm
from common.permissions import HasPermission


class OpportunityApplyView(APIView):
    """Candidature d'une entreprise à une opportunité (slug)."""

    permission_classes = [IsAuthenticated]

    def post(self, request, slug: str):
        opportunity = Opportunity.objects.filter(slug=slug).first()
        if opportunity is None:
            return Response(
                {"error": {"code": "not_found", "message": "Cette opportunité est introuvable."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        membership = (
            CompanyMember.objects.filter(user=request.user, is_active=True)
            .select_related("company")
            .order_by("-role")
            .first()
        )
        if membership is None:
            return Response(
                {
                    "error": {
                        "code": "no_company",
                        "message": "Créez votre profil entreprise pour candidater à un marché KEMTA.",
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        if not membership.can_manage:
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": "Seul le responsable de l'entreprise peut déposer une candidature.",
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = ApplicationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            application = submit_application(
                opportunity=opportunity,
                company=membership.company,
                submitted_by=request.user,
                data=serializer.validated_data,
            )
        except ValueError as exc:
            return Response(
                {"error": {"code": "not_allowed", "message": str(exc)}}, status=status.HTTP_409_CONFLICT
            )
        except PermissionError as exc:
            return Response(
                {"error": {"code": "plan_limit", "message": str(exc)}}, status=status.HTTP_402_PAYMENT_REQUIRED
            )
        return Response(
            {
                "message": "Votre candidature a été envoyée.",
                "reference": application.reference,
                "detail": (
                    "L'équipe KEMTA examine votre dossier et revient vers vous sous 5 jours ouvrés. "
                    "Suivez l'avancement depuis votre espace entreprise."
                ),
                "application": ApplicationDetailSerializer(application).data,
            },
            status=status.HTTP_201_CREATED,
        )


class MyApplicationViewSet(ReadOnlyModelViewSet):
    """Candidatures de l'entreprise connectée."""

    permission_classes = [IsAuthenticated]
    pagination_class = KemtaPageNumberPagination
    filterset_fields = ["status", "opportunity"]
    ordering = ["-created_at"]

    def _company(self):
        return getattr(self.request.user, "primary_company", None)

    def get_queryset(self):
        company = self._company()
        if company is None:
            if self.request.user.is_kemta_team:
                return Application.objects.select_related("company", "opportunity", "submitted_by")
            return Application.objects.none()
        return (
            Application.objects.filter(company=company)
            .select_related("company", "opportunity", "submitted_by")
            .prefetch_related("documents__asset", "relevant_realizations__cover")
        )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ApplicationDetailSerializer
        return ApplicationListSerializer

    @action(detail=True, methods=["post"], url_path="withdraw")
    def withdraw(self, request, pk=None):
        application = self.get_object()
        try:
            withdraw_application(application=application, actor=request.user)
        except ValueError as exc:
            return Response(
                {"error": {"code": "not_allowed", "message": str(exc)}}, status=status.HTTP_409_CONFLICT
            )
        return Response({"message": "Candidature retirée. Vous pouvez candidater à d'autres marchés."})

    @action(detail=False, methods=["get"], url_path="stats")
    def stats(self, request):
        company = self._company()
        if company is None:
            return Response(
                {"error": {"code": "no_company", "message": "Aucun profil entreprise associé à votre compte."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        aggregates = Application.objects.filter(company=company).aggregate(
            total=Count("id"),
            pending=Count("id", filter=Q(status__in=[ApplicationStatus.SUBMITTED, ApplicationStatus.REVIEWING])),
            shortlisted=Count("id", filter=Q(status__in=[ApplicationStatus.SHORTLISTED, ApplicationStatus.INTERVIEW])),
            awarded=Count("id", filter=Q(status=ApplicationStatus.AWARDED)),
            rejected=Count("id", filter=Q(status=ApplicationStatus.REJECTED)),
        )
        from django.db.models import Sum

        won_value = (
            Application.objects.filter(company=company, status=ApplicationStatus.AWARDED)
            .aggregate(total=Sum("estimated_budget_xaf"))["total"]
            or 0
        )
        from common.utils import humanize_amount

        return Response(
            {
                **aggregates,
                "win_rate": round((aggregates["awarded"] or 0) / (aggregates["total"] or 1) * 100, 1),
                "won_value_xaf": float(won_value),
                "won_value_label": humanize_amount(won_value),
            }
        )


class AdminApplicationViewSet(ModelViewSet):
    """Back-office : instruction des candidatures et décisions."""

    permission_classes = [IsAuthenticated, HasPermission(Perm.REVIEW_APPLICATION)]
    pagination_class = KemtaPageNumberPagination
    filterset_fields = ["status", "company", "opportunity", "submitted_by"]
    search_fields = ["reference", "company__name", "opportunity__title", "presentation"]
    ordering = ["-created_at"]

    def get_queryset(self):
        queryset = (
            Application.objects.select_related("company", "opportunity", "submitted_by", "reviewed_by")
            .prefetch_related("documents__asset", "relevant_realizations__cover")
            .all()
        )
        if self.request.query_params.get("pending") in {"1", "true"}:
            queryset = queryset.filter(status__in=[ApplicationStatus.SUBMITTED, ApplicationStatus.REVIEWING])
        return queryset

    def get_serializer_class(self):
        if self.request.method in {"PUT", "PATCH"}:
            return ApplicationReviewSerializer
        if self.action == "retrieve":
            return ApplicationDetailSerializer
        return ApplicationListSerializer

    def update(self, request, *args, **kwargs):
        application = self.get_object()
        serializer = ApplicationReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = review_application(
            application=application, reviewer=request.user, data=serializer.validated_data
        )
        return Response(ApplicationDetailSerializer(application).data)

    @action(detail=False, methods=["get"], url_path="stats")
    def stats(self, request):
        aggregates = Application.objects.aggregate(
            total=Count("id"),
            submitted=Count("id", filter=Q(status=ApplicationStatus.SUBMITTED)),
            reviewing=Count("id", filter=Q(status=ApplicationStatus.REVIEWING)),
            shortlisted=Count("id", filter=Q(status=ApplicationStatus.SHORTLISTED)),
            awarded=Count("id", filter=Q(status=ApplicationStatus.AWARDED)),
            rejected=Count("id", filter=Q(status=ApplicationStatus.REJECTED)),
        )
        by_opportunity = list(
            Application.objects.values("opportunity__title", "opportunity__reference")
            .annotate(total=Count("id"))
            .order_by("-total")[:10]
        )
        return Response({**aggregates, "by_opportunity": by_opportunity})
