"""API des opportunités BTP : vitrine publique et pilotage KEMTA."""
from __future__ import annotations

from django.db.models import Count, Prefetch, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from apps.opportunities.models import (
    Opportunity,
    OpportunityStatus,
    OpportunityVisibility,
)
from apps.opportunities.serializers import (
    OpportunityDetailSerializer,
    OpportunityListSerializer,
    OpportunityWriteSerializer,
)
from common.pagination import KemtaPageNumberPagination
from common.permission_codes import Perm
from common.permissions import HasPermission


class PublicOpportunityViewSet(ReadOnlyModelViewSet):
    """Opportunités ouvertes visibles par les entreprises (et le grand public)."""

    permission_classes = [AllowAny]
    pagination_class = KemtaPageNumberPagination
    lookup_field = "slug"

    def get_queryset(self):
        user = self.request.user
        queryset = (
            Opportunity.objects.filter(
                status__in=[OpportunityStatus.OPEN, OpportunityStatus.REVIEWING],
                published_at__isnull=False,
            )
            .select_related("location", "project")
            .prefetch_related(Prefetch("required_specialties"))
        )
        # Visibilité : certaines opportunités sont réservées aux entreprises inscrites/vérifiées.
        if not (user and user.is_authenticated):
            queryset = queryset.filter(visibility=OpportunityVisibility.PUBLIC)
        elif user.is_company_user or getattr(user, "primary_company", None):
            queryset = queryset.exclude(visibility=OpportunityVisibility.INVITED)
        elif not user.is_kemta_team:
            queryset = queryset.filter(visibility=OpportunityVisibility.PUBLIC)

        params = self.request.query_params
        if params.get("type"):
            queryset = queryset.filter(property_type=params["type"])
        if params.get("city"):
            queryset = queryset.filter(
                Q(location_text__icontains=params["city"]) | Q(location__name__icontains=params["city"])
            )
        if params.get("specialty"):
            queryset = queryset.filter(required_specialties__code=params["specialty"])
        if params.get("budget_min"):
            try:
                queryset = queryset.filter(budget_max_xaf__gte=float(params["budget_min"]))
            except ValueError:
                pass
        if params.get("open") in {"1", "true"}:
            queryset = queryset.filter(application_deadline__gte=timezone.localdate())
        if params.get("search"):
            search = params["search"]
            queryset = queryset.filter(Q(title__icontains=search) | Q(description__icontains=search))

        ordering = params.get("ordering") or "-is_featured"
        if ordering == "deadline":
            queryset = queryset.order_by("application_deadline")
        elif ordering == "budget":
            queryset = queryset.order_by("-budget_max_xaf")
        elif ordering == "recent":
            queryset = queryset.order_by("-published_at")
        else:
            queryset = queryset.order_by("-is_featured", "-published_at")
        return queryset.distinct()

    def get_serializer_class(self):
        if self.action == "retrieve":
            return OpportunityDetailSerializer
        return OpportunityListSerializer

    def retrieve(self, request, *args, **kwargs):
        opportunity = self.get_object()
        opportunity.register_view()
        context = {"request": request}
        data = OpportunityDetailSerializer(opportunity, context=context).data
        if not request.user.is_authenticated:
            # Les données commerciales internes ne sortent jamais publiquement.
            for field in ("client_name", "internal_notes"):
                data.pop(field, None)
        return Response(data)

    @action(detail=False, methods=["get"], url_path="stats")
    def stats(self, request):
        """Indicateurs d'attractivité de la place de marché."""
        base = Opportunity.objects.filter(status=OpportunityStatus.OPEN, published_at__isnull=False)
        aggregates = base.aggregate(
            total=Count("id"),
            open=Count("id", filter=Q(application_deadline__gte=timezone.localdate())),
            featured=Count("id", filter=Q(is_featured=True)),
        )
        by_type = list(base.values("property_type").annotate(total=Count("id")).order_by("-total")[:8])
        return Response({**aggregates, "by_type": by_type})
