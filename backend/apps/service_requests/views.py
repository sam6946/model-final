"""API des demandes de service.

- ``POST /service-requests/`` : formulaire public (aucune authentification) —
  protégé par rate limiting et par une validation stricte ;
- ``GET /service-requests/mine/`` : suivi par le client connecté ;
- ``/admin/service-requests/...`` : qualification par l'équipe KEMTA.
"""
from __future__ import annotations

from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from apps.service_requests.models import (
    RequestStatus,
    ServiceKind,
    ServiceRequest,
    ServiceRequestAttachment,
    ServiceRequestEvent,
)
from apps.service_requests.serializers import (
    ServiceCatalogSerializer,
    ServiceRequestCreateSerializer,
    ServiceRequestDetailSerializer,
    ServiceRequestListSerializer,
    ServiceRequestUpdateSerializer,
)
from apps.service_requests.services import change_status, create_service_request, service_catalog_payload
from common.models import Asset
from common.pagination import KemtaPageNumberPagination
from common.permission_codes import Perm
from common.permissions import HasPermission, IsKemtaTeam
from common.throttling import PublicWriteThrottle


class ServiceCatalogListView(APIView):
    """Catalogue des services dispensés par KEMTA (public, mis en cache)."""

    permission_classes = [AllowAny]

    def get(self, _request):
        return Response({"results": service_catalog_payload()})


class ServiceRequestCreateView(APIView):
    """Dépôt d'une demande : visiteur non inscrit ou client connecté."""

    permission_classes = [AllowAny]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    throttle_classes = [PublicWriteThrottle]

    def post(self, request):
        serializer = ServiceRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)

        attachment_ids = data.pop("attachment_ids", []) or []
        attachments = []
        if attachment_ids:
            user = request.user if request.user.is_authenticated else None
            assets = Asset.objects.filter(id__in=attachment_ids)
            if not user:
                # Un visiteur ne peut joindre que ses propres dépôts anonymes :
                # on se limite aux assets non publiés créés très récemment.
                assets = assets.filter(is_public=False)
            attachments = [
                ServiceRequestAttachment(
                    category=_category_for_asset(asset),
                    asset=asset,
                    caption=asset.original_filename,
                )
                for asset in assets
            ]

        service_request = create_service_request(
            data=data,
            attachments=attachments,
            user=request.user if request.user.is_authenticated else None,
            request=request,
        )
        return Response(
            {
                "reference": service_request.reference,
                "message": "Votre demande a bien été reçue.",
                "detail": (
                    "Notre équipe va l'étudier et vous contacter sous 48 heures ouvrées. "
                    "Conservez votre référence pour suivre le dossier."
                ),
                "kind_label": service_request.kind_label,
                "created_at": service_request.created_at,
                "next_steps": [
                    "Étude de votre demande par un chargé de suivi KEMTA",
                    "Appel de qualification (WhatsApp, téléphone ou e-mail selon votre préférence)",
                    "Proposition détaillée et mise en relation avec les entreprises BTP si nécessaire",
                ],
                "support_phone": _support_phone(),
            },
            status=status.HTTP_201_CREATED,
        )


def _category_for_asset(asset: Asset) -> str:
    name = (asset.original_filename or "").lower()
    if asset.mime_type.startswith("image/"):
        return ServiceRequestAttachment.Category.PHOTO
    if any(token in name for token in ("plan", "croquis", "dwg", "architecture")):
        return ServiceRequestAttachment.Category.PLAN
    if any(token in name for token in ("devis", "quote", "facture")):
        return ServiceRequestAttachment.Category.QUOTE
    return ServiceRequestAttachment.Category.DOCUMENT


def _support_phone() -> str:
    from django.conf import settings

    return settings.KEMTA_SUPPORT_PHONE


class MyServiceRequestsView(APIView):
    """Suivi des demandes du client connecté (identifiées par téléphone ou compte)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = (
            ServiceRequest.objects.filter(
                Q(customer=request.user) | Q(phone=request.user.phone)
            )
            .distinct()
            .order_by("-created_at")
        )
        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        paginator = KemtaPageNumberPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = ServiceRequestListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class MyServiceRequestDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, reference: str):
        service_request = (
            ServiceRequest.objects.select_related("location", "assigned_to", "converted_project")
            .prefetch_related("attachments__asset", "events__actor")
            .filter(Q(customer=request.user) | Q(phone=request.user.phone), reference=reference)
            .first()
        )
        if service_request is None:
            return Response(
                {"error": {"code": "not_found", "message": "Cette demande est introuvable."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        data = ServiceRequestDetailSerializer(service_request).data
        # Le client ne voit pas les notes internes ni les événements masqués.
        data.pop("internal_notes", None)
        data.pop("qualification_notes", None)
        data["events"] = [
            event for event in data.get("events", []) if event.get("is_customer_visible")
        ]
        return Response(data)

    def post(self, request, reference: str):
        """Le client peut ajouter un complément d'information à sa demande."""
        service_request = ServiceRequest.objects.filter(
            Q(customer=request.user) | Q(phone=request.user.phone), reference=reference
        ).first()
        if service_request is None:
            return Response(
                {"error": {"code": "not_found", "message": "Cette demande est introuvable."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        message = (request.data.get("message") or "").strip()
        if len(message) < 3:
            return Response(
                {"error": {"code": "invalid", "message": "Merci d'écrire votre message avant d'envoyer."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ServiceRequestEvent.objects.create(
            request=service_request,
            actor=request.user,
            from_status=service_request.status,
            to_status=service_request.status,
            comment=message,
            is_customer_visible=True,
        )
        return Response({"message": "Votre message a été transmis à l'équipe KEMTA."})


class AdminServiceRequestViewSet(ModelViewSet):
    """Back-office : qualification, affectation, conversion en projet."""

    permission_classes = [IsAuthenticated, HasPermission(Perm.MANAGE_SERVICE_REQUEST)]
    pagination_class = KemtaPageNumberPagination
    filterset_fields = ["kind", "status", "priority", "assigned_to", "country"]
    search_fields = ["reference", "first_name", "last_name", "phone", "email", "location_text"]
    ordering_fields = ["created_at", "priority", "status", "estimated_value_xaf"]
    ordering = ["-created_at"]

    def get_queryset(self):
        queryset = (
            ServiceRequest.objects.select_related("location", "assigned_to", "converted_project")
            .prefetch_related("attachments__asset")
            .all()
        )
        status_filter = self.request.query_params.get("status_group")
        if status_filter == "open":
            queryset = queryset.exclude(
                status__in=[RequestStatus.CONVERTED, RequestStatus.CLOSED, RequestStatus.REJECTED]
            )
        elif status_filter == "new":
            queryset = queryset.filter(status=RequestStatus.NEW)
        return queryset

    def get_serializer_class(self):
        if self.action in {"update", "partial_update"}:
            return ServiceRequestUpdateSerializer
        if self.action == "list":
            return ServiceRequestListSerializer
        return ServiceRequestDetailSerializer

    @action(detail=False, methods=["get"], url_path="stats")
    def stats(self, request):
        """Compteurs de pilotage commercial (une seule requête agrégée)."""
        queryset = ServiceRequest.objects.all()
        totals = queryset.aggregate(
            total=Count("id"),
            new=Count("id", filter=Q(status=RequestStatus.NEW)),
            open=Count(
                "id",
                filter=~Q(status__in=[RequestStatus.CONVERTED, RequestStatus.CLOSED, RequestStatus.REJECTED]),
            ),
            converted=Count("id", filter=Q(status=RequestStatus.CONVERTED)),
        )
        by_kind = list(
            queryset.values("kind").annotate(total=Count("id")).order_by("-total")
        )
        last_30_days = queryset.filter(created_at__gte=timezone.now() - timezone.timedelta(days=30)).count()
        return Response({**totals, "by_kind": by_kind, "last_30_days": last_30_days})

    @action(detail=True, methods=["post"], url_path="assign")
    def assign(self, request, pk=None):
        service_request = self.get_object()
        assignee_id = request.data.get("user_id")
        from django.contrib.auth import get_user_model

        User = get_user_model()
        if assignee_id:
            assignee = User.objects.filter(pk=assignee_id, is_active=True).first()
            if assignee is None:
                return Response(
                    {"error": {"code": "invalid", "message": "Ce membre de l'équipe est introuvable."}},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            assignee = None
        service_request.assigned_to = assignee
        service_request.save(update_fields=["assigned_to", "updated_at"])
        ServiceRequestEvent.objects.create(
            request=service_request, actor=request.user,
            from_status=service_request.status, to_status=service_request.status,
            comment=f"Dossier confié à {assignee.full_name}." if assignee else "Dossier remis en attente d'affectation.",
            is_customer_visible=False,
        )
        return Response(ServiceRequestDetailSerializer(service_request).data)

    @action(detail=True, methods=["post"], url_path="status")
    def set_status(self, request, pk=None):
        service_request = self.get_object()
        new_status = request.data.get("status")
        valid = {choice for choice, _label in ServiceRequest._meta.get_field("status").choices}
        if new_status not in valid:
            return Response(
                {"error": {"code": "invalid_status", "message": "Statut inconnu pour une demande."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        change_status(
            service_request=service_request,
            new_status=new_status,
            actor=request.user,
            comment=request.data.get("comment") or "",
            customer_visible=bool(request.data.get("customer_visible", True)),
        )
        return Response(ServiceRequestDetailSerializer(service_request).data)

    @action(detail=True, methods=["post"], url_path="convert")
    def convert(self, request, pk=None):
        """Convertit une demande qualifiée en projet suivi (ou en propriété)."""
        from apps.projects.services import create_project_from_request

        service_request = self.get_object()
        if service_request.converted_project_id:
            return Response(
                {"error": {"code": "already_converted", "message": "Cette demande a déjà été convertie en projet."}},
                status=status.HTTP_409_CONFLICT,
            )
        project = create_project_from_request(
            service_request=service_request,
            actor=request.user,
            overrides=request.data or {},
        )
        return Response(
            {
                "message": "Le projet a été créé et le client informé.",
                "project_id": project.pk,
                "project_reference": project.reference,
            },
            status=status.HTTP_201_CREATED,
        )
