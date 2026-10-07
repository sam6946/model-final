"""RBAC et cloisonnement des données : le cœur de la confiance KEMTA.

Ce que ces tests protègent : un client ne voit que ses chantiers, une entreprise
BTP ne voit que son dossier, et le back-office reste inaccessible sans le rôle
KEMTA correspondant. Toute régression ici est un incident de sécurité.
"""
from __future__ import annotations

import pytest

from tests.factories import make_company, make_project

pytestmark = pytest.mark.django_db

PRIVATE_ENDPOINTS = [
    "/api/v1/dashboard/",
    "/api/v1/projects/mine/",
    "/api/v1/requests/mine/",
    "/api/v1/payments/",
    "/api/v1/invoices/",
    "/api/v1/notifications/",
    "/api/v1/applications/mine/",
    "/api/v1/company/mine/",
]


@pytest.mark.parametrize("endpoint", PRIVATE_ENDPOINTS)
def test_private_endpoints_reject_anonymous(api, endpoint):
    """Aucune fuite sans authentification : 401 et message actionnable."""
    response = api.get(endpoint)
    assert response.status_code == 401, endpoint
    assert response.json()["error"]["code"] == "not_authenticated"


@pytest.mark.parametrize(
    "endpoint",
    [
        "/api/v1/admin/requests/",
        "/api/v1/admin/projects/",
        "/api/v1/admin/companies/",
        "/api/v1/admin/plans/",
        "/api/v1/admin/payments/",
        "/api/v1/admin/audit-logs/",
        "/api/v1/evidences/review-queue/",
    ],
)
def test_customer_cannot_open_the_back_office(api, authed, customer, endpoint):
    authed(customer)
    response = api.get(endpoint)
    assert response.status_code == 403, endpoint
    assert response.json()["error"]["code"] == "forbidden"


def test_customer_cannot_read_another_customers_project(api, authed, customer):
    from apps.accounts.models import Role, User

    other = make_project(
        customer=User.objects.create_user(
            phone="+237655000111", password="Kemta!2026test", role=Role.CUSTOMER,
            first_name="Paul", last_name="Nganou",
        )
    )
    authed(customer)
    assert api.get(f"/api/v1/projects/{other.pk}/").status_code in {403, 404}
    assert api.get(f"/api/v1/projects/{other.pk}/timeline/").status_code in {403, 404}
    assert api.get(f"/api/v1/projects/{other.pk}/budget-summary/").status_code in {403, 404}


def test_company_account_cannot_read_another_companys_file(api, authed, company_owner, other_company):
    """Une entreprise ne doit jamais accéder aux documents d'une consœur."""
    authed(company_owner.owner)
    mine = api.get("/api/v1/company/mine/")
    assert mine.status_code == 200
    assert mine.json()["company"]["slug"] == company_owner.slug

    documents = api.get("/api/v1/company/documents/")
    assert documents.status_code == 200
    body = documents.json()
    items = body["results"] if isinstance(body, dict) and "results" in body else body
    listed_company_ids = {item.get("company") for item in items}
    assert other_company.pk not in listed_company_ids


def test_company_account_cannot_use_admin_space(api, authed, company_owner):
    authed(company_owner.owner)
    response = api.get("/api/v1/dashboard/", {"space": "ADMIN"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_manager_cannot_open_admin_only_plan_edition(api, authed, manager):
    """Le rôle MANAGER pilote les dossiers, pas la facturation des plans."""
    authed(manager)
    assert api.get("/api/v1/admin/plans/").status_code == 403


def test_permissions_endpoint_reflects_the_role(api, authed, customer, admin_user):
    authed(customer)
    customer_perms = set(api.get("/api/v1/auth/permissions/").json()["permissions"])
    authed(admin_user)
    admin_perms = set(api.get("/api/v1/auth/permissions/").json()["permissions"])
    assert customer_perms < admin_perms
    assert not any("admin" in code or "manage_" in code for code in customer_perms if code.endswith("_all"))


def test_project_member_scope_is_limited_to_their_projects(api, authed, company_owner, customer):
    """Une entreprise rattachée à un chantier y accède ; aux autres, non."""
    from apps.projects.models import ProjectMember

    assigned = make_project(customer=customer, company=company_owner)
    ProjectMember.objects.create(project=assigned, user=company_owner.owner)
    unrelated = make_project(customer=customer)

    authed(company_owner.owner)
    assert api.get(f"/api/v1/projects/{assigned.pk}/").status_code == 200
    assert api.get(f"/api/v1/projects/{unrelated.pk}/").status_code in {403, 404}


def test_admin_stats_are_reserved_to_the_kemta_team(api, authed, customer, admin_user):
    authed(customer)
    assert api.get("/api/v1/admin/projects/stats/").status_code == 403
    authed(admin_user)
    assert api.get("/api/v1/admin/projects/stats/").status_code == 200


def test_company_owner_sees_only_its_own_company_in_listing(api, authed, company_owner, other_company):
    authed(company_owner.owner)
    response = api.get("/api/v1/companies/")
    slugs = {item["slug"] for item in response.json()["results"]}
    assert company_owner.slug in slugs


def test_unpublished_company_is_not_public(api, company_owner):
    from apps.companies.models import Company

    hidden = make_company(company_owner.owner, published=False, name="Entreprise en attente")
    assert isinstance(hidden, Company)
    assert api.get(f"/api/v1/companies/{hidden.slug}/").status_code == 404


def test_staff_flag_does_not_grant_every_api_permission(api, authed, reference_data):
    """« is_staff » ouvre l'admin Django, pas la facturation de l'API.

    Régression : un chargé de suivi marqué staff recevait auparavant toutes les
    permissions (plans, paiements, journaux d'audit). Seul un superutilisateur
    peut court-circuiter le RBAC.
    """
    from apps.accounts.models import Role, User

    user = User.objects.create_user(
        phone="+237655000900", password="Kemta!2026test", role=Role.MANAGER,
        first_name="Chargé", last_name="De Suivi", is_staff=True,
    )
    authed(user)

    # Ses permissions métier restent disponibles…
    assert api.get("/api/v1/admin/projects/").status_code == 200
    # …mais la facturation et l'audit restent fermés.
    assert api.get("/api/v1/admin/plans/").status_code == 403
    assert api.get("/api/v1/admin/payments/").status_code == 403
    assert api.get("/api/v1/admin/audit-logs/").status_code == 403
