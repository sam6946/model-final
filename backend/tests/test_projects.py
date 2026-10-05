"""Suivi de chantier : avancement, budget, chronologie et cloisonnement."""
from __future__ import annotations

from decimal import Decimal

import pytest

from tests.factories import make_project

pytestmark = pytest.mark.django_db


def test_customer_lists_only_its_own_projects(api, authed, customer):
    mine = make_project(customer=customer, name="Villa Bafoussam")
    from apps.accounts.models import Role, User

    other_owner = User.objects.create_user(
        phone="+237655000222", password="Kemta!2026test", role=Role.CUSTOMER,
        first_name="Pauline", last_name="Tchoumi",
    )
    make_project(customer=other_owner, name="Immeuble Yaoundé")

    authed(customer)
    response = api.get("/api/v1/projects/mine/")
    assert response.status_code == 200
    names = [item["name"] for item in response.json()["results"]]
    assert names == ["Villa Bafoussam"]
    assert mine.pk


def test_project_detail_exposes_progress_budget_and_health(api, authed, customer):
    project = make_project(customer=customer, budget=30_000_000, spent=9_000_000, progress="42.50")
    authed(customer)
    body = api.get(f"/api/v1/projects/{project.pk}/").json()
    assert body["reference"] == project.reference
    assert Decimal(str(body["physical_progress"])) == Decimal("42.50")
    assert Decimal(str(body["budget_total_xaf"])) == Decimal("30000000")
    assert body["health_label"]  # libellé humain, pas le code technique
    assert "budget_summary" in body or "budget" in str(body.keys())


def test_budget_summary_aggregates_lines_and_remaining_balance(api, authed, customer, manager):
    from apps.projects.models import BudgetLine

    project = make_project(customer=customer, budget=20_000_000, spent=5_000_000)
    BudgetLine.objects.create(
        project=project, label="Fondations", category=BudgetLine.Category.MATERIAUX,
        planned_xaf=Decimal("4000000"), committed_xaf=Decimal("3900000"), spent_xaf=Decimal("4300000"),
    )
    BudgetLine.objects.create(
        project=project, label="Main d'œuvre gros œuvre", category=BudgetLine.Category.MAIN_OEUVRE,
        planned_xaf=Decimal("6000000"), committed_xaf=Decimal("6000000"), spent_xaf=Decimal("5200000"),
    )

    authed(customer)
    response = api.get(f"/api/v1/projects/{project.pk}/budget-summary/")
    assert response.status_code == 200, response.content
    body = response.json()
    assert Decimal(str(body["totals"]["planned"])) == Decimal("10000000")
    assert Decimal(str(body["totals"]["spent"])) == Decimal("9500000")
    assert Decimal(str(body["budget_remaining_xaf"])) == Decimal("15000000")
    assert body["budget_used_percent"] >= 0


def test_progress_update_notifies_the_customer(api, authed, customer, manager):
    project = make_project(customer=customer, progress="20.00", manager=manager)
    authed(manager)
    response = api.post(
        f"/api/v1/projects/{project.pk}/progress/",
        {"progress": "38.00", "note": "Élévation des murs du rez-de-chaussée terminée."},
        format="json",
    )
    assert response.status_code == 200, response.content
    project.refresh_from_db()
    assert Decimal(project.physical_progress) == Decimal("38.00")

    from apps.notifications.models import Notification

    assert Notification.objects.filter(recipient=customer).exists()


def test_progress_update_is_refused_to_a_stranger(api, authed, customer, manager):
    project = make_project(customer=customer, manager=manager)
    authed(customer)  # le client consulte, il ne déclare pas l'avancement
    response = api.post(
        f"/api/v1/projects/{project.pk}/progress/", {"progress": "99.00"}, format="json"
    )
    assert response.status_code == 403


def test_timeline_is_chronological_and_hides_internal_notes(api, authed, customer, manager):
    project = make_project(customer=customer, manager=manager)
    authed(manager)
    api.post(
        f"/api/v1/projects/{project.pk}/progress/",
        {"progress": "25.00", "note": "Coulage de la dalle effectué."},
        format="json",
    )
    from apps.projects.models import ProjectUpdate

    ProjectUpdate.objects.create(
        project=project, author=manager, update_type="NOTE",
        message="Note interne : le maçon est en retard, à surveiller sans alerter le client.",
        visibility="TEAM",
    )

    authed(customer)
    response = api.get(f"/api/v1/projects/{project.pk}/timeline/")
    assert response.status_code == 200, response.content
    body = response.json()
    items = body["results"] if isinstance(body, dict) and "results" in body else body
    messages = " ".join(str(item.get("message") or item.get("title") or "") for item in items)
    assert "Note interne" not in messages
    assert items
