"""Demandes de service : dépôt public, référence lisible, suivi et conversion."""
from __future__ import annotations

import re

import pytest

from apps.service_requests.models import ServiceRequest, ServiceRequestEvent

pytestmark = pytest.mark.django_db

ENDPOINT = "/api/v1/requests/"

FOLLOW_UP_PAYLOAD = {
    "kind": "EXISTING_SITE",
    "first_name": "Aïcha",
    "last_name": "Mbarga",
    "phone": "+237699112233",
    "city": "Bafoussam",
    "city_of_residence": "Montréal",
    "project_type": "Villa en construction",
    "location_text": "Bafoussam, quartier Administratif",
    "budget_min_xaf": "45 000 000",
    "budget_max_xaf": "60 000 000",
    "spent_xaf": "18 000 000",
    "description": "Je construis depuis la diaspora et je veux des preuves photo chaque semaine.",
    "current_progress": "FONDATIONS",
    "current_company": "Entreprise locale",
    "objective": "Sécuriser le budget et la qualité des travaux.",
    "terms_accepted": True,
}


def test_public_request_creates_readable_reference(api):
    """Un visiteur non inscrit peut déposer une demande et reçoit une référence."""
    response = api.post(ENDPOINT, FOLLOW_UP_PAYLOAD, format="json")
    assert response.status_code == 201, response.content
    body = response.json()
    assert re.match(r"^KEMTA-REQ-\d{4}-\d{6}$", body["reference"])
    assert body["message"] == "Votre demande a bien été reçue."
    assert body["next_steps"] and len(body["next_steps"]) >= 2
    assert body["support_phone"]

    request = ServiceRequest.objects.get(reference=body["reference"])
    assert request.phone == "+237699112233"  # numéro normalisé
    assert request.status == "NEW"
    assert ServiceRequestEvent.objects.filter(request=request).exists()


def test_request_requires_phone_and_terms_with_human_messages(api):
    response = api.post(ENDPOINT, {"kind": "BUILD_PROJECT", "first_name": "Jean", "last_name": "Etoa"}, format="json")
    assert response.status_code == 400
    fields = response.json()["error"]["fields"]
    assert "téléphone" in str(fields["phone"]).lower()
    assert "conditions" in str(fields["terms_accepted"]).lower() or "données" in str(
        fields["terms_accepted"]
    ).lower()
    assert "Invalid" not in str(fields)


def test_invalid_phone_is_refused_with_an_example(api):
    response = api.post(ENDPOINT, {**FOLLOW_UP_PAYLOAD, "phone": "12345"}, format="json")
    assert response.status_code == 400
    message = str(response.json()["error"]["fields"]["phone"])
    assert "+237" in message


def test_customer_only_sees_its_own_requests(api, authed, customer):
    mine = api.post(ENDPOINT, {**FOLLOW_UP_PAYLOAD, "phone": customer.phone}, format="json")
    assert mine.status_code == 201
    someone_else = api.post(
        ENDPOINT, {**FOLLOW_UP_PAYLOAD, "phone": "+237677889900", "first_name": "Autre"}, format="json"
    )
    assert someone_else.status_code == 201

    authed(customer)
    response = api.get("/api/v1/requests/mine/")
    assert response.status_code == 200
    references = {item["reference"] for item in response.json()["results"]}
    assert mine.json()["reference"] in references
    assert someone_else.json()["reference"] not in references

    detail = api.get(f"/api/v1/requests/mine/{mine.json()['reference']}/")
    assert detail.status_code == 200
    assert detail.json()["reference"] == mine.json()["reference"]


def test_follow_up_of_a_request_requires_authentication(api):
    assert api.get("/api/v1/requests/mine/").status_code == 401


def test_admin_qualifies_request_and_customer_sees_the_timeline(api, authed, customer, admin_user, manager):
    created = api.post(ENDPOINT, {**FOLLOW_UP_PAYLOAD, "phone": customer.phone}, format="json").json()
    request = ServiceRequest.objects.get(reference=created["reference"])

    authed(admin_user)
    assigned = api.post(
        f"/api/v1/admin/requests/{request.pk}/assign/", {"user_id": manager.pk}, format="json"
    )
    assert assigned.status_code in {200, 201}, assigned.content

    updated = api.post(
        f"/api/v1/admin/requests/{request.pk}/status/",
        {"status": "QUALIFIED", "comment": "Appel de qualification effectué."},
        format="json",
    )
    assert updated.status_code in {200, 201}, updated.content

    authed(customer)
    detail = api.get(f"/api/v1/requests/mine/{created['reference']}/")
    assert detail.status_code == 200
    events = detail.json().get("events", [])
    visible = [event for event in events if event.get("is_customer_visible")]
    assert any("qualification" in (event.get("comment") or "").lower() for event in visible)


def test_admin_converts_request_into_tracked_project(api, authed, customer, admin_user, manager):
    created = api.post(ENDPOINT, {**FOLLOW_UP_PAYLOAD, "phone": customer.phone}, format="json").json()
    request = ServiceRequest.objects.get(reference=created["reference"])
    request.status = "QUALIFIED"
    request.save(update_fields=["status", "updated_at"])

    authed(admin_user)
    response = api.post(
        f"/api/v1/admin/requests/{request.pk}/convert/",
        {"customer_id": customer.pk, "manager_id": manager.pk, "name": "Suivi villa Bafoussam"},
        format="json",
    )
    assert response.status_code in {200, 201}, response.content

    authed(customer)
    projects = api.get("/api/v1/projects/mine/").json()["results"]
    assert projects and projects[0]["name"] == "Suivi villa Bafoussam"
    assert projects[0]["reference"].startswith("KEMTA-PRJ-")


def test_request_listing_is_paginated(api, authed, admin_user):
    for index in range(3):
        api.post(
            ENDPOINT,
            {**FOLLOW_UP_PAYLOAD, "phone": f"+2376991122{index:02d}", "first_name": f"Client {index}"},
            format="json",
        )
    authed(admin_user)
    response = api.get("/api/v1/admin/requests/", {"page_size": 2})
    body = response.json()
    assert response.status_code == 200
    assert body["count"] >= 3
    assert len(body["results"]) == 2
    assert body["next"]
