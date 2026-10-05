"""Abonnements : les prix viennent du back-office, jamais du frontend."""
from __future__ import annotations

from decimal import Decimal

import pytest
from django.utils import timezone

from apps.subscriptions.models import Plan, PlanCode, Subscription

pytestmark = pytest.mark.django_db


def test_plans_are_public_and_priced_by_the_backend(api):
    response = api.get("/api/v1/plans/")
    assert response.status_code == 200
    body = response.json()
    plans = body["results"] if isinstance(body, dict) and "results" in body else body
    assert plans, "Les plans FREE / PRO / PREMIUM doivent être exposés par l'API."

    codes = {plan["code"].lower() for plan in plans}
    assert {"free", "pro", "premium"} <= codes
    for plan in plans:
        assert "price_xaf" in plan
        assert plan["currency"] == "XAF"
        assert "features" in plan
    free = next(plan for plan in plans if plan["code"].lower() == "free")
    assert Decimal(str(free["price_xaf"])) == Decimal("0")
    paid = next(plan for plan in plans if plan["code"].lower() == "pro")
    assert Decimal(str(paid["price_xaf"])) > 0
    assert paid["price_label"]


def test_plan_prices_are_configurable_by_the_kemta_team(api, authed, admin_user):
    authed(admin_user)
    plan = Plan.objects.get(code=PlanCode.PRO)
    updated = api.patch(
        f"/api/v1/admin/plans/{plan.pk}/",
        {"price_xaf": "39500", "tagline": "Le suivi sérieux, sans engagement long."},
        format="json",
    )
    assert updated.status_code == 200, updated.content

    plan.refresh_from_db()
    assert plan.price_xaf == Decimal("39500")

    # Le tarif public suit immédiatement la configuration du back-office.
    public = api.get("/api/v1/plans/").json()
    plans = public["results"] if isinstance(public, dict) and "results" in public else public
    pro = next(item for item in plans if item["code"].lower() == "pro")
    assert Decimal(str(pro["price_xaf"])) == Decimal("39500")


def test_customer_cannot_change_a_plan_price(api, authed, customer):
    plan = Plan.objects.get(code=PlanCode.PREMIUM)
    authed(customer)
    assert api.patch(
        f"/api/v1/admin/plans/{plan.pk}/", {"price_xaf": "1"}, format="json"
    ).status_code == 403
    plan.refresh_from_db()
    assert plan.price_xaf > Decimal("1")


def test_my_subscription_returns_an_explicit_empty_state(api, authed, customer):
    authed(customer)
    response = api.get("/api/v1/subscriptions/mine/")
    assert response.status_code == 200
    body = response.json()
    assert body.get("subscription") is None or body.get("plan") is None


def test_company_subscription_is_returned_with_limits(api, authed, company_owner):
    plan = Plan.objects.get(code=PlanCode.PREMIUM)
    Subscription.objects.create(
        company=company_owner,
        plan=plan,
        status="ACTIVE",
        current_period_end=timezone.now() + timezone.timedelta(days=30),
        price_xaf_snapshot=plan.price_xaf,
    )
    authed(company_owner.owner)
    response = api.get("/api/v1/subscriptions/mine/")
    assert response.status_code == 200
    body = response.json()
    subscription = body["subscription"]
    assert subscription["plan"]["code"].lower() == "premium"
    assert subscription["days_remaining"] >= 29
    assert "limits" in body
