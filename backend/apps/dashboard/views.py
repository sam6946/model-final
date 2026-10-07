"""Endpoint agrégé `GET /api/v1/dashboard/`.

Le frontend n'appelle qu'une seule URL au chargement d'un espace : moins de
requêtes, un temps perçu plus court, et une charge serveur maîtrisée.
"""
from __future__ import annotations

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.dashboard.services import (
    build_admin_dashboard,
    build_client_dashboard,
    build_company_dashboard,
    cached_dashboard,
)
from common.permission_codes import Perm
from common.permissions import get_user_permissions


class DashboardView(APIView):
    """Tableau de bord consolidé : client, entreprise BTP ou back-office KEMTA."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        space = (request.query_params.get("space") or "").upper()
        user = request.user

        # Le back-office consolidé (chiffre d'affaires, encaissements, dossiers
        # entreprises) n'est pas ouvert à toute l'équipe KEMTA : il exige le
        # droit de consulter les statistiques. L'équipe terrain (rôle FIELD)
        # n'a ni VIEW_STATISTICS ni VIEW_FINANCE — elle suit ses chantiers.
        can_back_office = bool(user.is_superuser) or Perm.VIEW_STATISTICS in get_user_permissions(user)

        if space == "ADMIN" or (not space and can_back_office):
            if not can_back_office:
                return Response(
                    {
                        "error": {
                            "code": "forbidden",
                            "message": "Cet espace est réservé à l'équipe KEMTA.",
                        }
                    },
                    status=403,
                )
            payload = build_admin_dashboard(user)
            return Response({**payload, "space": "ADMIN", "cache": {"hit": False}})

        if space == "COMPANY" or (not space and user.is_company_user):
            payload = build_company_dashboard(user)
            if payload.get("company") is None:
                return Response(
                    {**payload, "space": "COMPANY", "cache": {"hit": False}},
                    status=200,
                )
            return Response({**payload, "space": "COMPANY", "cache": {"hit": False}})

        payload, hit = cached_dashboard(
            user=user, namespace="dashboard_client", builder=build_client_dashboard
        )
        return Response({**payload, "space": "CUSTOMER", "cache": {"hit": hit}})
