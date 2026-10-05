"""API des abonnements : plans publics, souscription, administration des tarifs."""
from __future__ import annotations

from django.db.models import Count, Q, Sum
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from apps.subscriptions.models import Plan, Subscription
from apps.subscriptions.serializers import (
    PlanAdminSerializer,
    PlanSerializer,
    SubscribeSerializer,
    SubscriptionSerializer,
)
from apps.subscriptions.services import (
    check_application_capacity,
    check_realization_capacity,
    current_subscription,
    effective_limits,
    plans_payload,
    subscribe_company,
)
from common.pagination import KemtaPageNumberPagination
from common.permission_codes import Perm
from common.permissions import HasPermission


def _my_company(user):
    return getattr(user, "primary_company", None)


class PlanListView(APIView):
    """Plans d'abonnement BTP — les prix viennent du backend, jamais du front."""

    permission_classes = [AllowAny]

    def get(self, _request):
        return Response({"results": plans_payload()})


class MySubscriptionView(APIView):
    """Abonnement de l'entreprise : état, limites d'usage, historique."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        company = _my_company(request.user)
        if company is None:
            return Response(
                {
                    "subscription": None,
                    "limits": {},
                    "usage": {},
                    "message": "Créez votre profil entreprise pour choisir une offre.",
                }
            )
        subscription = current_subscription(company)
        limits = effective_limits(company)
        from apps.applications.models import Application
        from apps.btp_catalog.models import Realization
        from django.utils import timezone as tz

        month_start = tz.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        usage = {
            "realizations": Realization.objects.filter(company=company).exclude(status="ARCHIVED").count(),
            "applications_this_month": Application.objects.filter(
                company=company, created_at__gte=month_start
            ).count(),
        }
        invoices = (
            company.invoices.order_by("-issued_at")[:12]
        )
        from apps.payments.serializers import InvoiceSerializer

        return Response(
            {
                "company": {"id": company.pk, "name": company.name},
                "subscription": SubscriptionSerializer(subscription).data if subscription else None,
                "limits": limits,
                "usage": usage,
                "can_publish_realization": check_realization_capacity(company)[0],
                "can_apply": check_application_capacity(company)[0],
                "invoices": InvoiceSerializer(invoices, many=True).data,
            }
        )

    def post(self, request):
        """Souscription ou changement d'offre."""
        company = _my_company(request.user)
        if company is None:
            return Response(
                {"error": {"code": "no_company", "message": "Créez d'abord votre profil entreprise."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        membership = company.members.filter(user=request.user).first()
        if membership is None or not membership.can_manage:
            return Response(
                {"error": {"code": "forbidden", "message": "Seul le responsable de l'entreprise peut changer d'offre."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = SubscribeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan = Plan.objects.get(code=serializer.validated_data["plan_code"], is_active=True)
        try:
            subscription = subscribe_company(
                company=company, plan=plan, actor=request.user,
                provider=serializer.validated_data.get("provider", "MANUAL"),
            )
        except ValueError as exc:
            return Response({"error": {"code": "not_allowed", "message": str(exc)}}, status=status.HTTP_409_CONFLICT)

        payment_payload = None
        if not plan.is_free:
            from apps.payments.serializers import PaymentSerializer
            from apps.payments.services import initiate_payment

            payment = initiate_payment(
                kind="SUBSCRIPTION",
                provider=serializer.validated_data.get("provider", "MANUAL"),
                amount_xaf=plan.price_xaf,
                payer=request.user,
                company=company,
                subscription=subscription,
                invoice=subscription.invoices.order_by("-id").first(),
                payer_phone=serializer.validated_data.get("payer_phone", ""),
                actor=request.user,
            )
            payment_payload = PaymentSerializer(payment).data

        return Response(
            {
                "message": f"Offre {plan.name} activée."
                + (" Réglez la facture pour prolonger la période." if not plan.is_free else ""),
                "subscription": SubscriptionSerializer(subscription).data,
                "payment": payment_payload,
            },
            status=status.HTTP_201_CREATED,
        )

    def patch(self, request):
        """Modulation : résiliation à échéance ou réactivation du renouvellement."""
        company = _my_company(request.user)
        subscription = current_subscription(company) if company else None
        if subscription is None:
            return Response(
                {"error": {"code": "not_found", "message": "Aucun abonnement actif pour votre entreprise."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        membership = company.members.filter(user=request.user).first()
        if membership is None or not membership.can_manage:
            return Response(
                {"error": {"code": "forbidden", "message": "Seul le responsable de l'entreprise peut modifier l'abonnement."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        if request.data.get("cancel_at_period_end") is not None:
            subscription.cancel_at_period_end = bool(request.data["cancel_at_period_end"])
        if request.data.get("auto_renew") is not None:
            subscription.auto_renew = bool(request.data["auto_renew"])
        subscription.save(update_fields=["cancel_at_period_end", "auto_renew", "updated_at"])
        if subscription.cancel_at_period_end:
            return Response(
                {
                    "message": "Votre abonnement restera actif jusqu'à la fin de la période payée, puis s'arrêtera.",
                    "subscription": SubscriptionSerializer(subscription).data,
                }
            )
        return Response(
            {"message": "Renouvellement réactivé.", "subscription": SubscriptionSerializer(subscription).data}
        )


class AdminPlanViewSet(ModelViewSet):
    """Back-office : tarifs, limites et mise en avant des offres (sans redéploiement)."""

    permission_classes = [IsAuthenticated, HasPermission(Perm.MANAGE_SUBSCRIPTION)]
    serializer_class = PlanAdminSerializer
    pagination_class = KemtaPageNumberPagination
    queryset = Plan.objects.annotate(subscriptions_count_cache=Count("subscriptions")).all()
    filterset_fields = ["is_active", "is_public", "interval"]
    search_fields = ["code", "name", "tagline"]
    ordering = ["sort_order", "price_xaf"]

    def perform_update(self, serializer):
        plan = serializer.save()
        from common.cache import bump_version

        bump_version("plans")

    def perform_create(self, serializer):
        serializer.save()
        from common.cache import bump_version

        bump_version("plans")

    @action(detail=False, methods=["get"], url_path="stats")
    def stats(self, request):
        aggregates = Subscription.objects.aggregate(
            total=Count("id"),
            active=Count("id", filter=Q(status=Subscription.Status.ACTIVE)),
            trialing=Count("id", filter=Q(status=Subscription.Status.TRIALING)),
            past_due=Count("id", filter=Q(status=Subscription.Status.PAST_DUE)),
            mrr=Sum("price_xaf_snapshot", filter=Q(status=Subscription.Status.ACTIVE)),
        )
        by_plan = list(
            Subscription.objects.filter(status__in=[Subscription.Status.ACTIVE, Subscription.Status.TRIALING])
            .values("plan__code", "plan__name")
            .annotate(total=Count("id"))
            .order_by("-total")
        )
        from common.utils import humanize_amount

        return Response(
            {
                **aggregates,
                "by_plan": by_plan,
                "mrr_label": humanize_amount(aggregates["mrr"] or 0),
            }
        )
