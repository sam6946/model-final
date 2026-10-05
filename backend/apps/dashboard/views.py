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


class DashboardView(APIView):
    """Tableau de bord consolidé : client, entreprise BTP ou back-office KEMTA."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        space = (request.query_params.get("space") or "").upper()
        user = request.user

        if space == "ADMIN" or (not space and user.is_kemta_team):
            if not user.is_kemta_team:
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
