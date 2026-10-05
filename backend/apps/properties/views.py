"""API des propriétés : patrimoine du client et suivi d'entretien."""
from __future__ import annotations

from django.db.models import Count, Q
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from apps.properties.models import Property, PropertyPhoto
from apps.properties.serializers import (
    PropertyDetailSerializer,
    PropertyListSerializer,
    PropertyPhotoSerializer,
    PropertyWriteSerializer,
)
from common.pagination import KemtaPageNumberPagination
from common.permission_codes import Perm
from common.permissions import HasPermission


def _visible_properties(user):
    queryset = Property.objects.select_related("location", "cover", "manager")
    if user.is_kemta_team:
        return queryset
    return queryset.filter(Q(owner=user) | Q(manager=user)).distinct()


class MyPropertyViewSet(ModelViewSet):
    """Propriétés de l'utilisateur connecté (création incluse)."""

    permission_classes = [IsAuthenticated]
    pagination_class = KemtaPageNumberPagination
    filterset_fields = ["property_type", "occupancy_status", "city", "is_active"]
    search_fields = ["name", "reference", "city", "location_text", "address"]
    ordering = ["-created_at"]

    def get_queryset(self):
        queryset = _visible_properties(self.request.user).prefetch_related("photos__asset")
        if self.request.query_params.get("attention") in {"1", "true"}:
            from django.utils import timezone

            from apps.properties.models import OccupancyStatus

            threshold = timezone.now() - timezone.timedelta(days=60)
            queryset = queryset.filter(
                occupancy_status__in=[OccupancyStatus.VACANT, OccupancyStatus.GUARDED]
            ).filter(Q(last_visited_at__lt=threshold) | Q(last_visited_at__isnull=True))
        return queryset

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return PropertyWriteSerializer
        if self.action == "retrieve":
            return PropertyDetailSerializer
        return PropertyListSerializer

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def create(self, request, *args, **kwargs):
        """Renvoie la fiche complète : le client enchaîne directement sur l'écran de détail."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            PropertyDetailSerializer(serializer.instance, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(PropertyDetailSerializer(instance, context={"request": request}).data)

    @action(detail=False, methods=["get"], url_path="stats")
    def stats(self, request):
        queryset = _visible_properties(request.user)
        aggregates = queryset.aggregate(
            total=Count("id"),
            vacant=Count("id", filter=Q(occupancy_status="VACANT")),
            rented=Count("id", filter=Q(occupancy_status="RENTED")),
            inactive=Count("id", filter=Q(is_active=False)),
        )
        from common.utils import humanize_amount
        from django.db.models import Sum

        values = queryset.aggregate(total_value=Sum("estimated_value_xaf"), monthly_rent=Sum("monthly_rent_xaf"))
        return Response(
            {
                **aggregates,
                "estimated_portfolio_xaf": float(values["total_value"] or 0),
                "estimated_portfolio_label": humanize_amount(values["total_value"] or 0),
                "monthly_rent_label": humanize_amount(values["monthly_rent"] or 0),
            }
        )

    @action(detail=True, methods=["post"], url_path="photos")
    def add_photo(self, request, pk=None):
        prop = self.get_object()
        serializer = PropertyPhotoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        photo = serializer.save(property=prop)
        return Response(PropertyPhotoSerializer(photo).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="register-visit")
    def register_visit(self, request, pk=None):
        """Enregistre une visite de contrôle et met à jour l'état du bien."""
        prop = self.get_object()
        if not (request.user.is_kemta_team or prop.manager_id == request.user.pk or prop.owner_id == request.user.pk):
            return Response(
                {"error": {"code": "forbidden", "message": "Vous ne pouvez pas enregistrer de visite sur ce bien."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        score = request.data.get("condition_score")
        prop.register_visit(score=int(score) if score not in (None, "") else None)
        from apps.activities.services import record_activity

        record_activity(
            verb="VISIT_COMPLETED",
            message=f"Visite enregistrée sur {prop.name}",
            actor=request.user,
            property=prop,
            entity_type="Property",
            entity_id=prop.pk,
            visibility="CUSTOMER",
        )
        return Response(PropertyDetailSerializer(prop).data)


class AdminPropertyViewSet(ModelViewSet):
    """Back-office : portefeuille de biens suivi par KEMTA."""

    permission_classes = [IsAuthenticated, HasPermission(Perm.MANAGE_PROPERTY)]
    pagination_class = KemtaPageNumberPagination
    filterset_fields = ["property_type", "occupancy_status", "city", "is_active", "owner"]
    search_fields = ["name", "reference", "city", "owner__first_name", "owner__last_name", "owner__phone"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return Property.objects.select_related("location", "cover", "owner", "manager").all()

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return PropertyWriteSerializer
        if self.action == "retrieve":
            return PropertyDetailSerializer
        return PropertyListSerializer

    def perform_create(self, serializer):
        serializer.save(owner=self.request.data.get("owner") or self.request.user)
