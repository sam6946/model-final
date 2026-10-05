"""API du catalogue : réalisations publiques et gestion par l'entreprise."""
from __future__ import annotations

from django.db.models import Count, Prefetch, Q
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from apps.btp_catalog.models import Realization, RealizationMedia, RealizationStatus, RealizationType as RealizationTypeChoices
from apps.btp_catalog.serializers import (
    RealizationAdminSerializer,
    RealizationDetailSerializer,
    RealizationListSerializer,
    RealizationWriteSerializer,
)
from apps.companies.models import Company, CompanyMember, Specialty
from apps.companies.serializers import SpecialtySerializer
from common.pagination import KemtaPageNumberPagination
from common.permission_codes import Perm
from common.permissions import HasPermission


def _published_queryset():
    return (
        Realization.objects.filter(status=RealizationStatus.PUBLISHED, company__is_published=True)
        .select_related("company", "cover", "location")
        .prefetch_related(
            Prefetch("services", queryset=Specialty.objects.only("id", "name", "code")),
            Prefetch("media", queryset=RealizationMedia.objects.select_related("asset").order_by("order")),
        )
    )


class PublicRealizationViewSet(ReadOnlyModelViewSet):
    """Catalogue public des réalisations (filtrable par métier, ville, type)."""

    permission_classes = [AllowAny]
    pagination_class = KemtaPageNumberPagination
    lookup_field = "slug"

    def get_queryset(self):
        queryset = _published_queryset()
        params = self.request.query_params
        if params.get("company"):
            queryset = queryset.filter(company__slug=params["company"])
        if params.get("type"):
            queryset = queryset.filter(realization_type=params["type"])
        if params.get("specialty"):
            queryset = queryset.filter(services__code=params["specialty"])
        if params.get("city"):
            city = params["city"]
            queryset = queryset.filter(
                Q(location_text__icontains=city) | Q(location__name__icontains=city) | Q(company__city__icontains=city)
            )
        if params.get("year"):
            try:
                queryset = queryset.filter(year=int(params["year"]))
            except ValueError:
                pass
        if params.get("search"):
            search = params["search"]
            queryset = queryset.filter(Q(title__icontains=search) | Q(description__icontains=search))
        if params.get("min_surface"):
            try:
                queryset = queryset.filter(surface_m2__gte=float(params["min_surface"]))
            except ValueError:
                pass
        ordering = params.get("ordering") or "-is_featured"
        if ordering == "recent":
            queryset = queryset.order_by("-year", "-created_at")
        elif ordering == "surface":
            queryset = queryset.order_by("-surface_m2")
        else:
            queryset = queryset.order_by("-is_featured", "-year", "-created_at")
        return queryset.distinct()

    def get_serializer_class(self):
        if self.action == "retrieve":
            return RealizationDetailSerializer
        return RealizationListSerializer

    def retrieve(self, request, *args, **kwargs):
        realization = self.get_object()
        realization.register_view()
        data = self.get_serializer(realization).data
        related = (
            _published_queryset()
            .filter(company=realization.company)
            .exclude(pk=realization.pk)[:3]
        )
        data["more_from_company"] = RealizationListSerializer(related, many=True).data
        return Response(data)

    @action(detail=False, methods=["get"], url_path="filters")
    def filters(self, request):
        """Facettes de filtrage (une requête agrégée par dimension)."""
        base = _published_queryset()
        types = list(
            base.values("realization_type").annotate(total=Count("id")).order_by("-total")
        )
        labels = dict(RealizationTypeChoices)
        return Response(
            {
                "types": [
                    {"value": row["realization_type"], "label": labels.get(row["realization_type"], row["realization_type"]), "count": row["total"]}
                    for row in types
                ],
                "specialties": SpecialtySerializer(
                    Specialty.objects.filter(realizations__status=RealizationStatus.PUBLISHED, is_active=True)
                    .distinct()
                    .order_by("order"),
                    many=True,
                ).data,
            }
        )


class MyRealizationViewSet(ModelViewSet):
    """Réalisations de l'entreprise connectée (publication au catalogue)."""

    permission_classes = [IsAuthenticated]
    pagination_class = KemtaPageNumberPagination
    filterset_fields = ["status", "realization_type", "year"]
    search_fields = ["title", "description", "location_text"]
    ordering = ["order", "-year"]

    def _membership(self):
        return (
            CompanyMember.objects.filter(user=self.request.user, is_active=True)
            .select_related("company")
            .order_by("-role")
            .first()
        )

    def get_queryset(self):
        membership = self._membership()
        if membership is None:
            return Realization.objects.none()
        return (
            Realization.objects.filter(company=membership.company)
            .select_related("company", "cover", "location")
            .prefetch_related(
                Prefetch("services", queryset=Specialty.objects.only("id", "name", "code")),
                Prefetch("media", queryset=RealizationMedia.objects.select_related("asset").order_by("order")),
            )
        )

    def get_serializer_class(self):
        if self.request.method in {"POST", "PUT", "PATCH"}:
            return RealizationWriteSerializer
        return RealizationDetailSerializer

    def create(self, request, *args, **kwargs):
        membership = self._membership()
        if membership is None:
            return Response(
                {"error": {"code": "no_company", "message": "Créez d'abord votre profil entreprise."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        if not membership.can_manage and not membership.can_publish_catalog:
            return Response(
                {"error": {"code": "forbidden", "message": "Votre rôle ne permet pas de publier au catalogue."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        company = membership.company

        # Respect des limites du plan d'abonnement (valeurs issues du backend).
        from apps.subscriptions.services import check_realization_capacity

        allowed, message = check_realization_capacity(company)
        if not allowed:
            return Response(
                {"error": {"code": "plan_limit", "message": message}}, status=status.HTTP_402_PAYMENT_REQUIRED
            )

        serializer = RealizationWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        services = data.pop("services", [])
        media_items = data.pop("media", []) or []
        realization = Realization.objects.create(
            company=company,
            created_by=request.user,
            status=RealizationStatus.PENDING
            if company.verification_status != "VERIFIED"
            else RealizationStatus.PUBLISHED,
            **data,
        )
        if services:
            realization.services.set([item.pk for item in services])
        _attach_media(realization, media_items)

        from apps.activities.services import record_activity

        record_activity(
            verb="CATALOG_PUBLISHED",
            message=f"Réalisation « {realization.title} » publiée par {company.name}",
            actor=request.user,
            company=company,
            entity_type="Realization",
            entity_id=realization.pk,
            visibility="PUBLIC",
        )
        return Response(
            {
                "message": "Réalisation enregistrée."
                + (
                    " Elle sera visible après vérification de votre entreprise."
                    if realization.status == RealizationStatus.PENDING
                    else " Elle est visible dans le catalogue."
                ),
                "realization": RealizationDetailSerializer(realization).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        realization = self.get_object()
        membership = self._membership()
        if membership is None or membership.company_id != realization.company_id:
            return Response(
                {"error": {"code": "forbidden", "message": "Cette réalisation n'appartient pas à votre entreprise."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = RealizationWriteSerializer(realization, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        services = data.pop("services", None)
        media_items = data.pop("media", []) or []
        realization = serializer.save()
        if services is not None:
            realization.services.set([item.pk for item in services])
        _attach_media(realization, media_items)
        return Response(RealizationDetailSerializer(realization).data)

    def destroy(self, request, *args, **kwargs):
        realization = self.get_object()
        membership = self._membership()
        if membership is None or membership.company_id != realization.company_id:
            return Response(
                {"error": {"code": "forbidden", "message": "Cette réalisation n'appartient pas à votre entreprise."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        realization.status = RealizationStatus.ARCHIVED
        realization.save(update_fields=["status", "updated_at"])
        return Response({"message": "Réalisation archivée : elle n'apparaît plus au catalogue."})

    @action(detail=True, methods=["post"], url_path="media")
    def add_media(self, request, pk=None):
        realization = self.get_object()
        membership = self._membership()
        if membership is None or membership.company_id != realization.company_id:
            return Response(
                {"error": {"code": "forbidden", "message": "Action non autorisée."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        items = request.data.get("items") or [request.data]
        _attach_media(realization, items)
        return Response(RealizationDetailSerializer(realization).data, status=status.HTTP_201_CREATED)


class AdminRealizationViewSet(ModelViewSet):
    """Back-office : modération du catalogue."""

    permission_classes = [IsAuthenticated, HasPermission(Perm.MANAGE_CATALOG)]
    serializer_class = RealizationAdminSerializer
    pagination_class = KemtaPageNumberPagination
    filterset_fields = ["status", "realization_type", "company", "is_featured"]
    search_fields = ["title", "company__name", "location_text"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return Realization.objects.select_related("company", "cover").all()

    @action(detail=True, methods=["post"], url_path="decision")
    def decision(self, request, pk=None):
        realization = self.get_object()
        decision = request.data.get("status")
        if decision not in {"PUBLISHED", "REJECTED", "PENDING", "ARCHIVED"}:
            return Response(
                {"error": {"code": "invalid", "message": "Décision inconnue pour une réalisation."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        realization.status = decision
        if request.data.get("featured") is not None:
            realization.is_featured = bool(request.data["featured"])
        realization.save(update_fields=["status", "is_featured", "updated_at"])
        if decision == "REJECTED":
            from apps.notifications.services import notify
            from common.constants import NotificationType

            notify(
                recipient=realization.company.owner,
                notification_type=NotificationType.SYSTEM,
                title="Réalisation non publiée",
                body=(
                    f"« {realization.title} » n'a pas été publiée : "
                    f"{request.data.get('reason') or 'photos ou description insuffisantes'}."
                ),
                action_url="/entreprise/realisations",
                action_label="Corriger la réalisation",
                dedupe_key=f"realization:{realization.pk}:rejected",
            )
        return Response(RealizationAdminSerializer(realization).data)


def _attach_media(realization: Realization, items: list) -> list:
    created = []
    for index, item in enumerate(items or []):
        asset_id = item.get("asset") or item.get("asset_id")
        if not asset_id:
            continue
        created.append(
            RealizationMedia.objects.create(
                realization=realization,
                kind=item.get("kind") or RealizationMedia.MediaKind.PHOTO,
                asset_id=asset_id,
                caption=(item.get("caption") or "")[:180],
                order=item.get("order", index),
            )
        )
    return created


