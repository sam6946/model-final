"""Back-office : création et pilotage des opportunités BTP."""
from __future__ import annotations

from django.db.models import Count
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.notifications.services import notify
from apps.opportunities.models import Opportunity, OpportunityStatus
from apps.opportunities.serializers import OpportunityDetailSerializer, OpportunityWriteSerializer
from apps.applications.models import Application
from common.pagination import KemtaPageNumberPagination
from common.permission_codes import Perm
from common.permissions import HasPermission


class AdminOpportunityViewSet(ModelViewSet):
    """CRUD complet des opportunités, avec publication et relance ciblée."""

    permission_classes = [IsAuthenticated, HasPermission(Perm.MANAGE_OPPORTUNITY)]
    pagination_class = KemtaPageNumberPagination
    filterset_fields = ["status", "visibility", "property_type", "is_featured", "requires_verified_company"]
    search_fields = ["reference", "title", "location_text", "client_name"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return (
            Opportunity.objects.select_related("location", "project", "created_by")
            .prefetch_related("required_specialties")
            .annotate(applications_count_cache=Count("applications"))
            .all()
        )

    def get_serializer_class(self):
        if self.request.method in {"POST", "PUT", "PATCH"}:
            return OpportunityWriteSerializer
        return OpportunityDetailSerializer

    def perform_create(self, serializer):
        opportunity = serializer.save(created_by=self.request.user)
        if opportunity.status == OpportunityStatus.OPEN and opportunity.published_at is None:
            opportunity.published_at = timezone.now()
            opportunity.save(update_fields=["published_at"])
        self.created_instance = opportunity

    def create(self, request, *args, **kwargs):
        """Le back-office reçoit l'opportunité créée, prête à publier."""
        write = OpportunityWriteSerializer(data=request.data)
        write.is_valid(raise_exception=True)
        self.perform_create(write)
        opportunity = self.created_instance
        return Response(OpportunityDetailSerializer(opportunity).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="publish")
    def publish(self, request, pk=None):
        opportunity = self.get_object()
        if opportunity.application_deadline < timezone.localdate():
            return Response(
                {
                    "error": {
                        "code": "deadline_passed",
                        "message": "La date limite est dépassée : mettez-la à jour avant de publier.",
                    }
                },
                status=status.HTTP_409_CONFLICT,
            )
        opportunity.status = OpportunityStatus.OPEN
        opportunity.published_at = opportunity.published_at or timezone.now()
        opportunity.save(update_fields=["status", "published_at", "updated_at"])
        notified = self._notify_matching_companies(opportunity)
        from apps.activities.services import record_activity

        record_activity(
            verb="OPPORTUNITY_CREATED",
            message=f"Opportunité {opportunity.reference} publiée : {opportunity.title}",
            actor=request.user,
            entity_type="Opportunity",
            entity_id=opportunity.pk,
            visibility="PUBLIC",
            is_important=True,
        )
        return Response(
            {
                "message": f"Opportunité publiée. {notified} entreprise(s) pertinente(s) alertée(s).",
                "opportunity": OpportunityDetailSerializer(opportunity).data,
            }
        )

    def _notify_matching_companies(self, opportunity: Opportunity) -> int:
        """Alerte uniquement les entreprises réellement concernées (pertinence, pas spam)."""
        from apps.companies.models import Company, VerificationStatus

        queryset = Company.objects.filter(is_published=True).select_related("owner")
        if opportunity.requires_verified_company:
            queryset = queryset.filter(verification_status=VerificationStatus.VERIFIED)
        if opportunity.minimum_experience_years:
            queryset = queryset.filter(years_experience__gte=opportunity.minimum_experience_years)
        specialty_ids = list(opportunity.required_specialties.values_list("id", flat=True))
        if specialty_ids:
            queryset = queryset.filter(specialties__id__in=specialty_ids)
        count = 0
        for company in queryset.distinct()[:200]:
            notify(
                recipient=company.owner,
                notification_type="OPPORTUNITY",
                title=f"Nouveau marché : {opportunity.title}",
                body=(
                    f"{opportunity.display_location} · {opportunity.budget_label}. "
                    f"Candidatures ouvertes jusqu'au {opportunity.application_deadline}."
                ),
                action_url=f"/opportunites/{opportunity.slug}",
                action_label="Voir le marché",
                entity_type="Opportunity",
                entity_id=opportunity.pk,
                payload={"reference": opportunity.reference},
                dedupe_key=f"opportunity:{opportunity.pk}:company:{company.pk}",
            )
            count += 1
        return count

    @action(detail=True, methods=["get"], url_path="applications")
    def applications(self, request, pk=None):
        opportunity = self.get_object()
        queryset = (
            opportunity.applications.select_related("company", "submitted_by")
            .order_by("-created_at")
        )
        from apps.applications.serializers import ApplicationListSerializer

        paginator = KemtaPageNumberPagination()
        page = paginator.paginate_queryset(queryset, request)
        return paginator.get_paginated_response(ApplicationListSerializer(page, many=True).data)

    @action(detail=False, methods=["get"], url_path="stats")
    def stats(self, request):
        aggregates = Opportunity.objects.aggregate(
            total=Count("id"),
            open=Count("id", filter=Q(status=OpportunityStatus.OPEN)),
            awarded=Count("id", filter=Q(status=OpportunityStatus.AWARDED)),
            featured=Count("id", filter=Q(is_featured=True)),
        )
        applications = Application.objects.aggregate(
            total=Count("id"),
            pending=Count("id", filter=Q(status__in=["SUBMITTED", "REVIEWING"])),
            awarded=Count("id", filter=Q(status="AWARDED")),
        )
        return Response({**aggregates, "applications": applications})
