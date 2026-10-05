"""API de l'entretien immobilier : contrats, visites, problèmes, planning terrain."""
from __future__ import annotations

from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from apps.maintenance.models import (
    MaintenanceContract,
    MaintenanceIssue,
    MaintenanceServiceType,
    MaintenanceVisit,
)
from apps.maintenance.serializers import (
    MaintenanceContractCreateSerializer,
    MaintenanceContractSerializer,
    MaintenanceIssueSerializer,
    MaintenanceServiceTypeSerializer,
    MaintenanceVisitSerializer,
)
from apps.maintenance.services import complete_visit, create_contract, report_issue
from apps.properties.models import Property
from common.pagination import KemtaPageNumberPagination
from common.permission_codes import Perm
from common.permissions import HasPermission


class MaintenanceServiceCatalogView(APIView):
    """Prestations d'entretien proposées (public, mis en cache côté client)."""

    permission_classes = [IsAuthenticated]

    def get(self, _request):
        services = MaintenanceServiceType.objects.filter(is_active=True).order_by("order", "name")
        return Response({"results": MaintenanceServiceTypeSerializer(services, many=True).data})


def _owned_property_ids(user):
    queryset = Property.objects.all()
    if not user.is_kemta_team:
        queryset = queryset.filter(Q(owner=user) | Q(manager=user))
    return queryset.values_list("id", flat=True)


class MaintenanceContractViewSet(ModelViewSet):
    """Contrats d'entretien du client (création, suivi, visites, problèmes)."""

    permission_classes = [IsAuthenticated]
    pagination_class = KemtaPageNumberPagination
    filterset_fields = ["status", "frequency", "property"]
    ordering = ["-created_at"]
    serializer_class = MaintenanceContractSerializer

    def get_queryset(self):
        property_ids = _owned_property_ids(self.request.user)
        return (
            MaintenanceContract.objects.filter(property_id__in=property_ids)
            .select_related("property", "customer", "assigned_team")
            .prefetch_related("services")
        )

    def create(self, request, *args, **kwargs):
        serializer = MaintenanceContractCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        prop = Property.objects.filter(pk=data["property"]).first()
        if prop is None:
            return Response(
                {"error": {"code": "not_found", "message": "Cette propriété est introuvable."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        if not (request.user.is_kemta_team or prop.owner_id == request.user.pk):
            return Response(
                {"error": {"code": "forbidden", "message": "Vous ne pouvez pas créer de contrat sur ce bien."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        contract = create_contract(data=data, customer=prop.owner, actor=request.user)
        return Response(MaintenanceContractSerializer(contract).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="generate-visits")
    def generate_visits(self, request, pk=None):
        contract = self.get_object()
        if not (request.user.is_kemta_team or contract.customer_id == request.user.pk):
            return Response(
                {"error": {"code": "forbidden", "message": "Action réservée au propriétaire du contrat."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        count = int(request.data.get("count") or contract.visits_included or 1)
        visits = contract.generate_next_visits(count=max(1, min(count, 12)))
        return Response(
            {
                "message": f"{len(visits)} visite(s) planifiée(s).",
                "visits": MaintenanceVisitSerializer(visits, many=True).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="pause")
    def pause(self, request, pk=None):
        contract = self.get_object()
        if not (request.user.is_kemta_team or contract.customer_id == request.user.pk):
            return Response(
                {"error": {"code": "forbidden", "message": "Action réservée au propriétaire du contrat."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        contract.status = MaintenanceContract.Status.PAUSED
        contract.save(update_fields=["status", "updated_at"])
        return Response(MaintenanceContractSerializer(contract).data)


class MaintenanceVisitViewSet(ModelViewSet):
    """Visites d'entretien : planning, réalisation, compte rendu."""

    permission_classes = [IsAuthenticated]
    serializer_class = MaintenanceVisitSerializer
    pagination_class = KemtaPageNumberPagination
    filterset_fields = ["status", "property", "technician", "contract"]
    ordering = ["-scheduled_for"]

    def get_queryset(self):
        property_ids = _owned_property_ids(self.request.user)
        queryset = MaintenanceVisit.objects.filter(
            Q(property_id__in=property_ids) | Q(technician=self.request.user)
        ).select_related("property", "technician").prefetch_related("services_performed")
        if self.request.query_params.get("upcoming") in {"1", "true"}:
            queryset = queryset.filter(scheduled_for__gte=timezone.now())
        if self.request.query_params.get("overdue") in {"1", "true"}:
            queryset = queryset.filter(
                scheduled_for__lt=timezone.now(), status__in=["SCHEDULED", "CONFIRMED"]
            )
        return queryset.distinct()

    def update(self, request, *args, **kwargs):
        visit = self.get_object()
        allowed = (
            request.user.is_kemta_team
            or visit.technician_id == request.user.pk
            or visit.property.owner_id == request.user.pk
        )
        if not allowed:
            return Response(
                {"error": {"code": "forbidden", "message": "Vous ne pouvez pas modifier cette visite."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().update(request, *args, **kwargs)

    @action(detail=True, methods=["post"], url_path="complete")
    def complete(self, request, pk=None):
        visit = self.get_object()
        if not (request.user.is_kemta_team or visit.technician_id == request.user.pk):
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": "Seul le technicien affecté (ou l'équipe KEMTA) peut clôturer cette visite.",
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        visit = complete_visit(
            visit=visit,
            actor=request.user,
            report=request.data.get("report", ""),
            score=request.data.get("condition_score"),
        )
        return Response(MaintenanceVisitSerializer(visit).data)

    @action(detail=False, methods=["get"], url_path="calendar")
    def calendar(self, request):
        """Planning regroupé par jour (une requête, prêt à afficher)."""
        queryset = self.get_queryset().filter(
            scheduled_for__gte=timezone.now() - timezone.timedelta(days=7),
            scheduled_for__lte=timezone.now() + timezone.timedelta(days=60),
        ).order_by("scheduled_for")[:200]
        grouped: dict[str, list] = {}
        for visit in queryset:
            key = timezone.localtime(visit.scheduled_for).date().isoformat()
            grouped.setdefault(key, []).append(visit)
        return Response(
            {
                "days": [
                    {"date": day, "visits": MaintenanceVisitSerializer(items, many=True).data}
                    for day, items in grouped.items()
                ]
            }
        )


class MaintenanceIssueViewSet(ModelViewSet):
    """Problèmes constatés sur les biens (devis, validation, réparation)."""

    permission_classes = [IsAuthenticated]
    serializer_class = MaintenanceIssueSerializer
    pagination_class = KemtaPageNumberPagination
    filterset_fields = ["status", "severity", "property"]
    ordering = ["-created_at"]

    def get_queryset(self):
        property_ids = _owned_property_ids(self.request.user)
        return MaintenanceIssue.objects.filter(property_id__in=property_ids).select_related("property", "photo")

    def create(self, request, *args, **kwargs):
        prop = Property.objects.filter(pk=request.data.get("property")).first()
        if prop is None:
            return Response(
                {"error": {"code": "not_found", "message": "Cette propriété est introuvable."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        allowed = request.user.is_kemta_team or prop.owner_id == request.user.pk or prop.manager_id == request.user.pk
        if not allowed:
            return Response(
                {"error": {"code": "forbidden", "message": "Vous ne pouvez pas signaler de problème sur ce bien."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not (request.data.get("title") or "").strip():
            return Response(
                {"error": {"code": "invalid", "message": "Décrivez le problème en quelques mots."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        issue = report_issue(prop=prop, data=request.data, actor=request.user)
        return Response(MaintenanceIssueSerializer(issue).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="status")
    def set_status(self, request, pk=None):
        issue = self.get_object()
        if not (request.user.is_kemta_team or issue.property.owner_id == request.user.pk):
            return Response(
                {"error": {"code": "forbidden", "message": "Vous ne pouvez pas modifier ce problème."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        new_status = request.data.get("status")
        valid = {choice for choice, _ in MaintenanceIssue.Status.choices}
        if new_status not in valid:
            return Response(
                {"error": {"code": "invalid", "message": "Statut inconnu pour un problème."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        issue.status = new_status
        if new_status == MaintenanceIssue.Status.FIXED:
            issue.resolved_at = timezone.now()
        issue.resolution_notes = (request.data.get("notes") or issue.resolution_notes)[:255]
        issue.save(update_fields=["status", "resolved_at", "resolution_notes", "updated_at"])
        return Response(MaintenanceIssueSerializer(issue).data)


class MaintenanceOverviewView(APIView):
    """Vue d'ensemble de l'entretien pour le client (agrégée, une requête)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        property_ids = list(_owned_property_ids(request.user))
        contracts = MaintenanceContract.objects.filter(property_id__in=property_ids)
        visits = MaintenanceVisit.objects.filter(property_id__in=property_ids)
        issues = MaintenanceIssue.objects.filter(property_id__in=property_ids)

        contracts_stats = contracts.aggregate(
            total=Count("id"),
            active=Count("id", filter=Q(status=MaintenanceContract.Status.ACTIVE)),
            paused=Count("id", filter=Q(status=MaintenanceContract.Status.PAUSED)),
        )
        visits_stats = visits.aggregate(
            total=Count("id"),
            upcoming=Count("id", filter=Q(scheduled_for__gte=timezone.now(), status__in=[
                MaintenanceVisit.Status.SCHEDULED, MaintenanceVisit.Status.CONFIRMED])),
            done=Count("id", filter=Q(status=MaintenanceVisit.Status.DONE)),
            overdue=Count("id", filter=Q(
                scheduled_for__lt=timezone.now(),
                status__in=[MaintenanceVisit.Status.SCHEDULED, MaintenanceVisit.Status.CONFIRMED],
            )),
        )
        issues_stats = issues.aggregate(
            total=Count("id"),
            open=Count("id", filter=~Q(status__in=[MaintenanceIssue.Status.FIXED, MaintenanceIssue.Status.IGNORED])),
            urgent=Count("id", filter=Q(severity__in=[
                MaintenanceIssue.Severity.HIGH, MaintenanceIssue.Severity.CRITICAL])),
        )
        next_visit = (
            visits.filter(
                scheduled_for__gte=timezone.now(),
                status__in=[MaintenanceVisit.Status.SCHEDULED, MaintenanceVisit.Status.CONFIRMED],
            )
            .select_related("property", "technician")
            .order_by("scheduled_for")
            .first()
        )
        return Response(
            {
                "contracts": contracts_stats,
                "visits": visits_stats,
                "issues": issues_stats,
                "properties_count": len(property_ids),
                "next_visit": MaintenanceVisitSerializer(next_visit).data if next_visit else None,
            }
        )
