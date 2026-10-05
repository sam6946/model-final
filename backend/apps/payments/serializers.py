"""Serializers des paiements et des factures."""
from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers

from apps.payments.models import Invoice, Payment, PaymentTransaction, Payout
from common.serializers import AssetSerializer
from common.utils import humanize_amount


class InvoiceSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    display_status = serializers.CharField(read_only=True)
    total_label = serializers.SerializerMethodField()
    paid_label = serializers.SerializerMethodField()
    balance_label = serializers.SerializerMethodField()
    balance_xaf = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    is_settled = serializers.BooleanField(read_only=True)
    pdf_detail = AssetSerializer(source="pdf", read_only=True)
    subscription_code = serializers.CharField(source="subscription.plan.code", read_only=True, default="")
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)

    class Meta:
        model = Invoice
        fields = (
            "id", "number", "kind", "kind_label", "currency", "subtotal_xaf", "tax_xaf",
            "total_xaf", "amount_paid_xaf", "balance_xaf", "status", "status_label",
            "display_status", "lines", "notes", "issued_at", "due_at", "paid_at",
            "total_label", "paid_label", "balance_label", "is_overdue", "is_settled",
            "pdf_detail", "subscription_code", "company", "project", "created_at",
        )

    def get_total_label(self, obj: Invoice) -> str:
        return humanize_amount(obj.total_xaf, obj.currency)

    def get_paid_label(self, obj: Invoice) -> str:
        return humanize_amount(obj.amount_paid_xaf, obj.currency)

    def get_balance_label(self, obj: Invoice) -> str:
        return humanize_amount(obj.balance_xaf, obj.currency)


class PaymentTransactionSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    provider_label = serializers.CharField(source="get_provider_display", read_only=True)

    class Meta:
        model = PaymentTransaction
        fields = (
            "id", "status", "status_label", "provider", "provider_label", "provider_event",
            "provider_transaction_id", "amount_xaf", "fees_xaf", "signature_verified",
            "failure_reason", "created_at",
        )


class PaymentSerializer(serializers.ModelSerializer):
    provider_label = serializers.CharField(source="get_provider_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    amount_label = serializers.SerializerMethodField()
    invoice_number = serializers.CharField(source="invoice.number", read_only=True, default="")
    transactions = PaymentTransactionSerializer(many=True, read_only=True)

    class Meta:
        model = Payment
        fields = (
            "id", "reference", "kind", "kind_label", "provider", "provider_label", "status",
            "status_label", "currency", "amount_xaf", "amount_label", "payer_phone",
            "checkout_url", "instructions", "provider_reference", "invoice_number",
            "failure_reason", "refunded_amount_xaf", "metadata", "transactions",
            "created_at", "paid_at", "expires_at", "company", "project", "subscription",
        )

    def get_amount_label(self, obj: Payment) -> str:
        return humanize_amount(obj.amount_xaf, obj.currency)


class PaymentInitiateSerializer(serializers.Serializer):
    """Demande de paiement : montant, moyen, et contexte métier."""

    kind = serializers.ChoiceField(
        choices=[
            ("SUBSCRIPTION", "Abonnement entreprise"),
            ("INVOICE", "Facture"),
            ("MILESTONE", "Décaissement par jalon"),
            ("ESCROW_FUNDING", "Alimentation du compte séquestre"),
            ("SERVICE_FEE", "Frais de service"),
        ],
        default="INVOICE",
    )
    provider = serializers.ChoiceField(
        choices=[
            ("MANUAL", "Virement / espèces"),
            ("MTN_MOMO", "MTN Mobile Money"),
            ("ORANGE_MONEY", "Orange Money"),
            ("CARD", "Carte bancaire"),
            ("BANK_TRANSFER", "Virement bancaire"),
        ],
        default="MANUAL",
    )
    amount_xaf = serializers.DecimalField(
        max_digits=14, decimal_places=2, min_value=Decimal("1"), required=False
    )
    invoice_id = serializers.IntegerField(required=False, allow_null=True)
    project_id = serializers.IntegerField(required=False, allow_null=True)
    subscription_id = serializers.IntegerField(required=False, allow_null=True)
    payer_phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    payer_email = serializers.EmailField(required=False, allow_blank=True)
    idempotency_key = serializers.CharField(max_length=140, required=False, allow_blank=True)
    note = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate_payer_phone(self, value: str) -> str:
        if not value:
            return value
        from common.utils import normalize_phone

        try:
            return normalize_phone(value)
        except ValueError as exc:
            raise serializers.ValidationError(
                "Ce numéro Mobile Money n'est pas valide. Exemple : +237 6 99 11 22 33."
            ) from exc

    def validate(self, attrs):
        from django.conf import settings

        if attrs.get("invoice_id") is None and not attrs.get("amount_xaf"):
            raise serializers.ValidationError({
                "amount_xaf": "Indiquez le montant à payer ou choisissez une facture."
            })
        if attrs.get("amount_xaf") and attrs["amount_xaf"] < settings.PAYMENT_MIN_AMOUNT_XAF:
            raise serializers.ValidationError({
                "amount_xaf": f"Le montant minimum est de {humanize_amount(settings.PAYMENT_MIN_AMOUNT_XAF)}."
            })
        if attrs["provider"] in {"MTN_MOMO", "ORANGE_MONEY"} and not attrs.get("payer_phone"):
            raise serializers.ValidationError({
                "payer_phone": "Le numéro de téléphone est nécessaire pour un paiement Mobile Money."
            })
        return attrs


class PaymentConfirmSerializer(serializers.Serializer):
    reference = serializers.CharField(max_length=80, required=False, allow_blank=True)
    provider_reference = serializers.CharField(max_length=120, required=False, allow_blank=True)
    note = serializers.CharField(required=False, allow_blank=True, max_length=255)


class PayoutSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    company_name = serializers.CharField(source="company.name", read_only=True, default="")
    project_reference = serializers.CharField(source="project.reference", read_only=True, default="")
    amount_label = serializers.SerializerMethodField()

    class Meta:
        model = Payout
        fields = (
            "id", "reference", "project", "project_reference", "company", "company_name",
            "budget_line", "label", "amount_xaf", "amount_label", "status", "status_label",
            "proof", "paid_at", "notes", "created_at",
        )

    def get_amount_label(self, obj: Payout) -> str:
        return humanize_amount(obj.amount_xaf)
