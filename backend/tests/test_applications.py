"""Opportunités et candidatures des entreprises BTP."""
from __future__ import annotations

import re

import pytest

from apps.applications.models import Application, ApplicationStatus
from tests.factories import make_company, make_opportunity

pytestmark = pytest.mark.django_db

PRESENTATION = (
    "Bâtisseurs du Wouri SARL est une entreprise générale de bâtiment basée à Bafoussam, "
    "spécialisée dans les villas haut de gamme et les immeubles locatifs. Nous disposons "
    "d'un parc matériel complet (bétonnière, vibreur, échafaudages) et d'une équipe "
    "permanente de 24 personnes, dont deux conducteurs de travaux diplômés."
)


def apply_payload(**overrides) -> dict:
    payload = {
        "presentation": PRESENTATION,
        "similar_experience": "Trois villas R+1 livrées à Bafoussam entre 2023 et 2025.",
        "methodology": "Planning hebdomadaire, approvisionnement par lots, photos quotidiennes.",
        "estimated_budget_xaf": "48000000",
        "proposed_duration_days": 210,
        "team_size": 22,
        "accepts_site_visit": True,
    }
    payload.update(overrides)
    return payload


def test_public_listing_shows_open_opportunities_only(api):
    make_opportunity(title="Villa R+1 à Bafoussam")
    make_opportunity(title="Candidatures closes", status="CLOSED", days_left=2)
    make_opportunity(title="Marché en préparation", status="DRAFT")

    response = api.get("/api/v1/opportunities/")
    assert response.status_code == 200
    titles = [item["title"] for item in response.json()["results"]]
    assert "Villa R+1 à Bafoussam" in titles
    assert "Candidatures closes" not in titles
    assert "Marché en préparation" not in titles


def test_verified_company_can_apply_and_receives_a_reference(api, authed, company_owner):
    opportunity = make_opportunity()
    authed(company_owner.owner)
    response = api.post(
        f"/api/v1/opportunities/{opportunity.slug}/apply/", apply_payload(), format="json"
    )
    assert response.status_code == 201, response.content
    body = response.json()
    assert re.match(r"^KEMTA-CAN-\d{4}-\d{5}$", body["reference"])
    assert "dossier" in body["message"].lower() or "candidature" in body["message"].lower()

    application = Application.objects.get(reference=body["reference"])
    assert application.company_id == company_owner.pk
    assert application.status == ApplicationStatus.SUBMITTED


def test_presentation_must_be_detailed_enough(api, authed, company_owner):
    opportunity = make_opportunity()
    authed(company_owner.owner)
    response = api.post(
        f"/api/v1/opportunities/{opportunity.slug}/apply/",
        apply_payload(presentation="Bonjour, je suis disponible."),
        format="json",
    )
    assert response.status_code == 400
    assert "80" in str(response.json()["error"])


def test_duplicate_application_is_refused(api, authed, company_owner):
    opportunity = make_opportunity()
    authed(company_owner.owner)
    assert api.post(
        f"/api/v1/opportunities/{opportunity.slug}/apply/", apply_payload(), format="json"
    ).status_code == 201
    second = api.post(
        f"/api/v1/opportunities/{opportunity.slug}/apply/", apply_payload(), format="json"
    )
    assert second.status_code in {400, 409}
    assert Application.objects.filter(opportunity=opportunity, company=company_owner).count() == 1


def test_unverified_company_cannot_apply_to_a_restricted_market(api, authed, other_company):
    opportunity = make_opportunity(requires_verified=True)
    authed(other_company.owner)
    response = api.post(
        f"/api/v1/opportunities/{opportunity.slug}/apply/", apply_payload(), format="json"
    )
    assert response.status_code in {403, 409}
    assert "vérifi" in str(response.json()).lower()


def test_expired_opportunity_no_longer_accepts_applications(api, authed, company_owner):
    opportunity = make_opportunity(days_left=-3)
    authed(company_owner.owner)
    response = api.post(
        f"/api/v1/opportunities/{opportunity.slug}/apply/", apply_payload(), format="json"
    )
    assert response.status_code in {400, 409}
    assert "closes" in str(response.json()).lower() or "limite" in str(response.json()).lower()


def test_user_without_company_is_invited_to_create_one(api, authed, customer, other_company):
    opportunity = make_opportunity()
    authed(customer)
    response = api.post(
        f"/api/v1/opportunities/{opportunity.slug}/apply/", apply_payload(), format="json"
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "no_company"


def test_company_sees_and_withdraws_only_its_own_applications(api, authed, company_owner):
    opportunity = make_opportunity()
    authed(company_owner.owner)
    reference = api.post(
        f"/api/v1/opportunities/{opportunity.slug}/apply/", apply_payload(), format="json"
    ).json()["reference"]

    mine = api.get("/api/v1/applications/mine/")
    assert mine.status_code == 200
    assert reference in {item["reference"] for item in mine.json()["results"]}

    application = Application.objects.get(reference=reference)
    withdrawn = api.post(f"/api/v1/applications/mine/{application.pk}/withdraw/", {}, format="json")
    assert withdrawn.status_code == 200, withdrawn.content
    application.refresh_from_db()
    assert application.status == ApplicationStatus.WITHDRAWN


def test_kemta_team_instructs_applications(api, authed, company_owner, admin_user, customer):
    opportunity = make_opportunity()
    authed(company_owner.owner)
    application = api.post(
        f"/api/v1/opportunities/{opportunity.slug}/apply/", apply_payload(), format="json"
    ).json()

    authed(admin_user)
    listing = api.get("/api/v1/admin/applications/", {"opportunity": opportunity.pk})
    assert listing.status_code == 200

    from apps.applications.models import Application as Model

    pk = Model.objects.get(reference=application["reference"]).pk
    reviewed = api.patch(
        f"/api/v1/admin/applications/{pk}/",
        {"status": ApplicationStatus.SHORTLISTED, "score": "82.5",
         "internal_notes": "Très bon dossier, références vérifiables."},
        format="json",
    )
    assert reviewed.status_code in {200, 201}, reviewed.content

    authed(company_owner.owner)
    detail = api.get(f"/api/v1/applications/mine/{pk}/")
    assert detail.json()["status"] == ApplicationStatus.SHORTLISTED


def test_company_cannot_see_another_companys_application(api, authed, company_owner, other_company):
    opportunity = make_opportunity()
    authed(company_owner.owner)
    application = api.post(
        f"/api/v1/opportunities/{opportunity.slug}/apply/", apply_payload(), format="json"
    ).json()

    from apps.applications.models import Application as Model

    pk = Model.objects.get(reference=application["reference"]).pk
    authed(other_company.owner)
    assert api.get(f"/api/v1/applications/mine/{pk}/").status_code in {403, 404}
    assert make_company  # la fabrique reste utilisée pour les fixtures de test
