"""API des paiements : initiation, suivi, webhooks, factures."""
from __future__ import annotations

import logging

from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from apps.payments.models import Invoice, InvoiceStatus, Payment, PaymentProvider, PaymentStatus, Payout
from apps.payments.serializers import (
    InvoiceSerializer,
    PaymentConfirmSerializer,
    PaymentInitiateSerializer,
    PaymentSerializer,
    PayoutSerializer,
)
from apps.payments.services import confirm_payment, handle_webhook, initiate_payment
from common.pagination import KemtaPageNumberPagination
from common.permission_codes import Perm
from common.permissions import HasPermission
from common.utils import humanize_amount
from common.throttling import PublicWriteThrottle

logger = logging.getLogger("kemta.payments.api")


class PaymentInitiateView(APIView):
    """Crée une intention de paiement (idempotente)."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [PublicWriteThrottle]

    def post(self, request):
        serializer = PaymentInitiateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        invoice = None
        amount = data.get("amount_xaf")
        if data.get("invoice_id"):
            invoice = Invoice.objects.filter(pk=data["invoice_id"]).first()
            if invoice is None:
                return Response(
                    {"error": {"code": "not_found", "message": "Cette facture est introuvable."}},
                    status=status.HTTP_404_NOT_FOUND,
                )
            allowed = (
                request.user.is_kemta_team
                or invoice.customer_id == request.user.pk
                or (invoice.company_id and invoice.company_id == getattr(request.user.primary_company, "pk", None))
            )
            if not allowed:
                return Response(
                    {"error": {"code": "forbidden", "message": "Cette facture ne vous appartient pas."}},
                    status=status.HTTP_403_FORBIDDEN,
                )
            amount = amount or invoice.balance_xaf

        project = None
        if data.get("project_id"):
            from apps.projects.models import Project

            project = Project.objects.filter(pk=data["project_id"]).first()
            if project is None:
                return Response(
                    {"error": {"code": "not_found", "message": "Ce projet est introuvable."}},
                    status=status.HTTP_404_NOT_FOUND,
                )
            if not (request.user.is_kemta_team or project.customer_id == request.user.pk
                    or project.members.filter(user=request.user).exists()):
                return Response(
                    {"error": {"code": "forbidden", "message": "Vous n'avez pas accès à ce projet."}},
                    status=status.HTTP_403_FORBIDDEN,
                )

        subscription = None
        if data.get("subscription_id"):
            from apps.subscriptions.models import Subscription

            subscription = Subscription.objects.filter(pk=data["subscription_id"]).first()
            if subscription is None:
                return Response(
                    {"error": {"code": "not_found", "message": "Cet abonnement est introuvable."}},
                    status=status.HTTP_404_NOT_FOUND,
                )
            if not (request.user.is_kemta_team or subscription.company_id == getattr(request.user.primary_company, "pk", None)):
                return Response(
                    {"error": {"code": "forbidden", "message": "Cet abonnement ne concerne pas votre entreprise."}},
                    status=status.HTTP_403_FORBIDDEN,
                )

        try:
            payment = initiate_payment(
                kind=data["kind"],
                provider=data["provider"],
                amount_xaf=amount,
                actor=request.user,
                company=getattr(request.user, "primary_company", None),
                project=project,
                invoice=invoice,
                subscription=subscription,
                payer_phone=data.get("payer_phone", ""),
                payer_email=data.get("payer_email", ""),
                idempotency_key=data.get("idempotency_key", ""),
                metadata={"note": data.get("note", "")},
            )
        except ValueError as exc:
            return Response({"error": {"code": "invalid_payment", "message": str(exc)}},
                            status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "message": payment.instructions or "Paiement initié.",
                "payment": PaymentSerializer(payment).data,
                "next_step": _next_step(payment),
            },
            status=status.HTTP_201_CREATED,
        )


def _next_step(payment: Payment) -> str:
    if payment.status == PaymentStatus.SUCCEEDED:
        return "Votre paiement est confirmé. Aucune action supplémentaire n'est nécessaire."
    if payment.checkout_url:
        return "Finalisez le paiement sur la page sécurisée ouverte dans votre navigateur."
    if payment.provider in {PaymentProvider.MTN_MOMO, PaymentProvider.ORANGE_MONEY}:
        return "Validez la demande reçue sur votre téléphone (code Mobile Money)."
    return (
        "Effectuez le virement puis transmettez la preuve à KEMTA. "
        "Votre dossier sera mis à jour dans les plus brefs délais."
    )


class PaymentWebhookView(APIView):
    """Webhook fournisseur : non authentifié, mais signature vérifiée et idempotent."""

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def post(self, request, provider: str):
        raw_body = request.body or b""
        signature = (
            request.headers.get("X-Kemta-Signature")
            or request.headers.get("X-Signature")
            or request.headers.get("X-Payment-Signature")
            or ""
        )
        event = handle_webhook(
            provider=provider.upper(),
            payload=request.data if isinstance(request.data, dict) else {},
            raw_body=raw_body,
            signature=signature,
        )
        return Response(
            {
                "received": True,
                "processed": event.processed,
                "event_id": event.event_id,
                "detail": event.error or "",
            }
        )


class MyPaymentViewSet(ReadOnlyModelViewSet):
    """Paiements du client ou de son entreprise."""

    permission_classes = [IsAuthenticated]
    serializer_class = PaymentSerializer
    pagination_class = KemtaPageNumberPagination
    filterset_fields = ["status", "provider", "kind", "project", "invoice"]
    ordering = ["-created_at"]

    def get_queryset(self):
        user = self.request.user
        queryset = Payment.objects.select_related("invoice", "company", "project", "subscription").prefetch_related("transactions")
        if user.is_kemta_team:
            return queryset
        company = getattr(user, "primary_company", None)
        condition = Q(payer=user) | Q(initiated_by=user) | Q(invoice__customer=user)
        if company is not None:
            condition |= Q(company=company)
        else:
            condition |= Q(company__members__user=user)
        return queryset.filter(condition).distinct()

    @action(detail=False, methods=["get"], url_path="stats")
    def stats(self, request):
        queryset = self.get_queryset()
        aggregates = queryset.aggregate(
            total=Count("id"),
            succeeded=Count("id", filter=Q(status=PaymentStatus.SUCCEEDED)),
            pending=Count("id", filter=Q(status__in=[PaymentStatus.PENDING, PaymentStatus.PROCESSING])),
            failed=Count("id", filter=Q(status=PaymentStatus.FAILED)),
            paid_total=Sum("amount_xaf", filter=Q(status=PaymentStatus.SUCCEEDED)),
        )
        return Response(
            {
                **aggregates,
                "paid_total_label": humanize_amount(aggregates["paid_total"] or 0),
            }
        )


class MyInvoiceViewSet(ReadOnlyModelViewSet):
    """Factures du client ou de son entreprise."""

    permission_classes = [IsAuthenticated]
    serializer_class = InvoiceSerializer
    pagination_class = KemtaPageNumberPagination
    filterset_fields = ["status", "kind", "company", "project"]
    ordering = ["-issued_at"]

    def get_queryset(self):
        user = self.request.user
        queryset = Invoice.objects.select_related("company", "customer", "subscription__plan", "pdf")
        if user.is_kemta_team:
            return queryset
        company = getattr(user, "primary_company", None)
        condition = Q(customer=user)
        if company is not None:
            condition |= Q(company=company)
        return queryset.filter(condition).distinct()

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        queryset = self.get_queryset()
        aggregates = queryset.aggregate(
            total=Count("id"),
            unpaid=Count("id", filter=Q(status__in=[InvoiceStatus.SENT, InvoiceStatus.PARTIALLY_PAID, InvoiceStatus.OVERDUE])),
            overdue=Count("id", filter=Q(due_at__lt=timezone.localdate()) & ~Q(status__in=[InvoiceStatus.PAID, InvoiceStatus.VOID])),
            total_amount=Sum("total_xaf"),
            paid_amount=Sum("amount_paid_xaf"),
        )
        outstanding = (aggregates["total_amount"] or 0) - (aggregates["paid_amount"] or 0)
        return Response(
            {
                **aggregates,
                "outstanding_label": humanize_amount(outstanding),
            }
        )


class AdminPaymentViewSet(ModelViewSet):
    """Back-office : suivi des encaissements, confirmation manuelle, décaissements."""

    permission_classes = [IsAuthenticated, HasPermission(Perm.MANAGE_PAYMENT)]
    serializer_class = PaymentSerializer
    pagination_class = KemtaPageNumberPagination
    filterset_fields = ["status", "provider", "kind", "company", "payer"]
    search_fields = ["reference", "provider_reference", "payer__phone", "payer_phone"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return Payment.objects.select_related("invoice", "company", "payer", "subscription").prefetch_related("transactions")

    @action(detail=True, methods=["post"], url_path="confirm")
    def confirm(self, request, pk=None):
        payment = self.get_object()
        if payment.is_succeeded:
            return Response(
                {"message": "Ce paiement était déjà confirmé.", "payment": PaymentSerializer(payment).data}
            )
        serializer = PaymentConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment = confirm_payment(
            payment=payment,
            actor=request.user,
            provider_reference=serializer.validated_data.get("provider_reference", ""),
        )
        return Response({"message": "Paiement confirmé.", "payment": PaymentSerializer(payment).data})

    @action(detail=True, methods=["post"], url_path="fail")
    def fail(self, request, pk=None):
        payment = self.get_object()
        payment.mark_failed(reason=request.data.get("reason") or "Marqué en échec par le back-office")
        return Response({"message": "Paiement marqué en échec.", "payment": PaymentSerializer(payment).data})

    @action(detail=False, methods=["get"], url_path="stats")
    def stats(self, request):
        aggregates = Payment.objects.aggregate(
            total=Count("id"),
            succeeded=Count("id", filter=Q(status=PaymentStatus.SUCCEEDED)),
            pending=Count("id", filter=Q(status__in=[PaymentStatus.PENDING, PaymentStatus.PROCESSING])),
            failed=Count("id", filter=Q(status=PaymentStatus.FAILED)),
            collected=Sum("amount_xaf", filter=Q(status=PaymentStatus.SUCCEEDED)),
        )
        by_provider = list(
            Payment.objects.values("provider").annotate(
                total=Count("id"), amount=Sum("amount_xaf", filter=Q(status=PaymentStatus.SUCCEEDED))
            ).order_by("-amount")
        )
        unpaid_invoices = Invoice.objects.filter(
            status__in=[InvoiceStatus.SENT, InvoiceStatus.PARTIALLY_PAID, InvoiceStatus.OVERDUE]
        ).aggregate(total=Count("id"), amount=Sum("total_xaf"))
        return Response(
            {
                **aggregates,
                "collected_label": humanize_amount(aggregates["collected"] or 0),
                "by_provider": by_provider,
                "unpaid_invoices": unpaid_invoices,
            }
        )


class AdminInvoiceViewSet(ModelViewSet):
    """Back-office : émission et suivi des factures."""

    permission_classes = [IsAuthenticated, HasPermission(Perm.MANAGE_PAYMENT)]
    serializer_class = InvoiceSerializer
    pagination_class = KemtaPageNumberPagination
    filterset_fields = ["status", "kind", "company", "customer", "project"]
    search_fields = ["number", "company__name", "customer__phone"]
    ordering = ["-issued_at"]

    def get_queryset(self):
        return Invoice.objects.select_related("company", "customer", "subscription__plan", "pdf")

    def create(self, request, *args, **kwargs):
        from common.models import ReferenceCounter

        serializer = InvoiceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invoice = serializer.save(number=ReferenceCounter.next_reference("FAC"), created_by=request.user)
        return Response(InvoiceSerializer(invoice).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="send")
    def send(self, request, pk=None):
        invoice = self.get_object()
        invoice.status = InvoiceStatus.SENT
        invoice.save(update_fields=["status", "updated_at"])
        from apps.notifications.services import notify
        from common.constants import NotificationType

        if invoice.customer_id:
            notify(
                recipient=invoice.customer,
                notification_type=NotificationType.PAYMENT,
                title=f"Facture {invoice.number} disponible",
                body=(
                    f"Montant : {humanize_amount(invoice.total_xaf)}. "
                    f"Échéance : {invoice.due_at or 'à réception'}."
                ),
                action_url="/espace/paiements",
                action_label="Régler la facture",
                entity_type="Invoice",
                entity_id=invoice.pk,
                payload={"reference": invoice.number, "amount_label": humanize_amount(invoice.total_xaf)},
                dedupe_key=f"invoice:{invoice.pk}:sent",
            )
        return Response({"message": "Facture transmise.", "invoice": InvoiceSerializer(invoice).data})


class AdminPayoutViewSet(ModelViewSet):
    """Back-office : décaissements vers les entreprises et fournisseurs."""

    permission_classes = [IsAuthenticated, HasPermission(Perm.MANAGE_FINANCE)]
    serializer_class = PayoutSerializer
    pagination_class = KemtaPageNumberPagination
    filterset_fields = ["status", "project", "company"]
    ordering = ["-created_at"]
    queryset = Payout.objects.select_related("project", "company", "budget_line")

    def perform_create(self, serializer):
        serializer.save(requested_by=self.request.user)

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        payout = self.get_object()
        if payout.status != Payout.Status.REQUESTED:
            return Response(
                {"error": {"code": "invalid_state", "message": "Ce décaissement a déjà été traité."}},
                status=status.HTTP_409_CONFLICT,
            )
        payout.status = Payout.Status.APPROVED
        payout.approved_by = request.user
        payout.save(update_fields=["status", "approved_by", "updated_at"])
        return Response(PayoutSerializer(payout).data)

    @action(detail=True, methods=["post"], url_path="mark-paid")
    def mark_paid(self, request, pk=None):
        payout = self.get_object()
        payout.status = Payout.Status.PAID
        payout.paid_at = timezone.now()
        payout.save(update_fields=["status", "paid_at", "updated_at"])
        return Response(PayoutSerializer(payout).data)
