"""Tableau de bord agrégé : une requête = tout l'écran d'accueil."""
from __future__ import annotations

import pytest

from apps.notifications.models import Notification, NotificationType
from tests.factories import make_company, make_project

pytestmark = pytest.mark.django_db

ENDPOINT = "/api/v1/dashboard/"

REQUIRED_KEYS = {
    "user",
    "statistics",
    "permissions",
    "projects",
    "organizations",
    "notifications",
    "recent_activity",
}


def test_customer_dashboard_returns_the_aggregated_payload(api, authed, customer):
    make_project(customer=customer, name="Villa Bafoussam")
    Notification.objects.create(
        recipient=customer,
        notification_type=NotificationType.PROJECT,
        title="Nouvelles photos disponibles",
        body="Trois photos de la dalle ont été validées par l'équipe KEMTA.",
    )

    authed(customer)
    response = api.get(ENDPOINT)
    assert response.status_code == 200, response.content
    body = response.json()
    assert REQUIRED_KEYS <= set(body)
    assert body["space"] == "CUSTOMER"
    assert body["user"]["first_name"] == "Aïcha"
    assert body["user"]["phone"].startswith("+237")
    assert body["statistics"]["projects"]["total"] == 1
    assert body["notifications"] and body["notifications"][0]["title"]
    assert body["permissions"]


def test_dashboard_is_cached_and_then_invalidated_by_activity(api, authed, customer):
    authed(customer)
    first = api.get(ENDPOINT).json()
    second = api.get(ENDPOINT).json()
    assert second["statistics"] == first["statistics"]

    make_project(customer=customer, name="Nouveau projet")
    third = api.get(ENDPOINT).json()
    assert third["statistics"]["projects"]["total"] > first["statistics"]["projects"]["total"]


def test_new_project_appears_with_its_health_label(api, authed, customer, manager):
    project = make_project(customer=customer, manager=manager, name="Suivi villa Ouest")
    authed(customer)
    body = api.get(ENDPOINT).json()
    card = next(item for item in body["projects"] if item["reference"] == project.reference)
    assert card["name"] == "Suivi villa Ouest"
    assert card["health_label"]
    assert card["progress_percent"] == 35.0


def test_company_dashboard_lists_organizations_and_opportunities(api, authed, company_owner):
    authed(company_owner.owner)
    response = api.get(ENDPOINT)
    assert response.status_code == 200, response.content
    body = response.json()
    assert body["space"] == "COMPANY"
    assert body["company"]["name"] == company_owner.name
    assert body["company"]["verification_status"] == "VERIFIED"
    assert "opportunities" in body["statistics"] or "applications" in body["statistics"]


def test_admin_dashboard_is_richer_than_the_customer_one(api, authed, admin_user, customer):
    authed(admin_user)
    admin_body = api.get(ENDPOINT).json()
    assert admin_body["space"] == "ADMIN"
    assert "requests" in admin_body["statistics"] or "projects" in admin_body["statistics"]

    authed(customer)
    assert api.get(ENDPOINT, {"space": "ADMIN"}).status_code == 403


def test_dashboard_permissions_are_the_same_as_the_permissions_endpoint(api, authed, customer):
    authed(customer)
    dashboard = api.get(ENDPOINT).json()
    permissions = api.get("/api/v1/auth/permissions/").json()
    assert set(dashboard["permissions"]) == set(permissions["permissions"])


def test_dashboard_recent_activity_is_limited(api, authed, admin_user):
    authed(admin_user)
    body = api.get(ENDPOINT).json()
    assert isinstance(body["recent_activity"], list)
    assert len(body["recent_activity"]) <= 20
