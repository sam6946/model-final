"""Serializers des plans et abonnements."""
from __future__ import annotations

from rest_framework import serializers

from apps.subscriptions.models import Plan, Subscription


class PlanSerializer(serializers.ModelSerializer):
    price_label = serializers.CharField(read_only=True)
    monthly_equivalent_xaf = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    is_free = serializers.BooleanField(read_only=True)

    class Meta:
        model = Plan
        fields = (
            "id", "code", "name", "tagline", "description", "price_xaf", "price_label",
            "currency", "interval", "trial_days", "features", "limits", "is_recommended",
            "is_free", "monthly_equivalent_xaf", "sort_order",
        )


class PlanAdminSerializer(serializers.ModelSerializer):
    subscriptions_count = serializers.SerializerMethodField()

    class Meta:
        model = Plan
        fields = (
            "id", "code", "name", "tagline", "description", "price_xaf", "currency",
            "interval", "trial_days", "features", "limits", "is_public", "is_active",
            "is_recommended", "sort_order", "subscriptions_count", "updated_at",
        )

    def get_subscriptions_count(self, obj: Plan) -> int:
        cache = getattr(obj, "subscriptions_count_cache", None)
        return cache if cache is not None else obj.subscriptions.count()


class SubscriptionSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    days_remaining = serializers.IntegerField(read_only=True)
    renews_soon = serializers.BooleanField(read_only=True)
    company_name = serializers.CharField(source="company.name", read_only=True)
    is_trial = serializers.BooleanField(read_only=True)

    class Meta:
        model = Subscription
        fields = (
            "id", "company", "company_name", "plan", "status", "status_label", "started_at",
            "current_period_start", "current_period_end", "trial_ends_at", "cancelled_at",
            "cancel_at_period_end", "price_xaf_snapshot", "seats", "provider", "auto_renew",
            "applications_used", "days_remaining", "renews_soon", "is_trial", "created_at",
        )


class SubscribeSerializer(serializers.Serializer):
    plan_code = serializers.CharField(max_length=40)
    provider = serializers.ChoiceField(
        choices=[
            ("MANUAL", "Virement / espèces"), ("MTN_MOMO", "MTN Mobile Money"),
            ("ORANGE_MONEY", "Orange Money"), ("CARD", "Carte bancaire"),
        ],
        default="MANUAL",
    )
    payer_phone = serializers.CharField(max_length=20, required=False, allow_blank=True)

    def validate_plan_code(self, value: str) -> str:
        if not Plan.objects.filter(code=value, is_active=True).exists():
            raise serializers.ValidationError("Cette offre n'existe pas ou n'est plus disponible.")
        return value

    def validate_payer_phone(self, value: str) -> str:
        if not value:
            return value
        from common.utils import normalize_phone

        try:
            return normalize_phone(value)
        except ValueError as exc:
            raise serializers.ValidationError(
                "Ce numéro de paiement n'est pas valide. Exemple : +237 6 99 11 22 33."
            ) from exc
