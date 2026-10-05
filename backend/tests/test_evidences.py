"""Preuves terrain : dépôt, revue par l'équipe KEMTA, synchronisation hors ligne."""
from __future__ import annotations

from decimal import Decimal

import pytest

from tests.factories import make_asset, make_project

pytestmark = pytest.mark.django_db


@pytest.fixture
def project(customer, manager):
    return make_project(customer=customer, manager=manager)


def test_photo_evidence_requires_a_file(api, authed, manager, project):
    authed(manager)
    response = api.post(
        f"/api/v1/projects/{project.pk}/evidences/",
        {"kind": "PHOTO", "title": "Fondations", "project": project.pk},
        format="json",
    )
    assert response.status_code == 400
    message = str(response.json()["error"])
    assert "fichier" in message.lower()


def test_team_uploads_photo_evidence_then_kemta_validates_it(api, authed, manager, admin_user, project, customer):
    asset = make_asset(manager)
    authed(manager)
    created = api.post(
        f"/api/v1/projects/{project.pk}/evidences/",
        {
            "project": project.pk,
            "kind": "PHOTO",
            "title": "Fondations coulées",
            "caption": "Semelles et amorces de poteaux, côté nord.",
            "asset": asset.pk,
            "captured_at": "2026-09-28T08:15:00Z",
            "latitude": "5.478100",
            "longitude": "10.417600",
            "accuracy_meters": 12,
            "is_offline_capture": True,
        },
        format="json",
    )
    assert created.status_code == 201, created.content
    evidence = created.json()
    assert evidence["status"] == "PENDING"
    assert evidence["status_label"] == "En attente de validation"

    authed(admin_user)
    queue = api.get("/api/v1/evidences/review-queue/")
    assert queue.status_code == 200
    body = queue.json()
    items = body["results"] if isinstance(body, dict) and "results" in body else body
    assert any(item["id"] == evidence["id"] for item in items)

    reviewed = api.post(
        f"/api/v1/projects/{project.pk}/evidences/{evidence['id']}/review/",
        {"action": "validate", "comment": "Conforme au planning."},
        format="json",
    )
    assert reviewed.status_code == 200, reviewed.content
    assert reviewed.json()["status"] == "VALIDATED"

    authed(customer)
    seen = api.get(f"/api/v1/projects/{project.pk}/evidences/")
    assert seen.status_code == 200
    ids = [item["id"] for item in seen.json()["results"]]
    assert evidence["id"] in ids


def test_rejection_requires_a_reason_for_the_field_team(api, authed, manager, admin_user, project):
    asset = make_asset(manager)
    authed(manager)
    evidence = api.post(
        f"/api/v1/projects/{project.pk}/evidences/",
        {"project": project.pk, "kind": "PHOTO", "asset": asset.pk},
        format="json",
    ).json()

    authed(admin_user)
    refused = api.post(
        f"/api/v1/projects/{project.pk}/evidences/{evidence['id']}/review/",
        {"action": "reject"},
        format="json",
    )
    assert refused.status_code == 400
    assert "motif" in str(refused.json()["error"]).lower()


def test_customer_cannot_upload_or_review_evidence(api, authed, customer, project):
    authed(customer)
    asset = make_asset(customer)
    upload = api.post(
        f"/api/v1/projects/{project.pk}/evidences/",
        {"project": project.pk, "kind": "PHOTO", "asset": asset.pk},
        format="json",
    )
    assert upload.status_code == 403
    assert api.get("/api/v1/evidences/review-queue/").status_code == 403


def test_stranger_cannot_read_evidence_of_a_project(api, authed, manager, customer, project):
    asset = make_asset(manager)
    authed(manager)
    api.post(
        f"/api/v1/projects/{project.pk}/evidences/",
        {"project": project.pk, "kind": "PHOTO", "asset": asset.pk},
        format="json",
    )

    outsider = type(customer).objects.create_user(
        phone="+237655000333", password="Kemta!2026test", role="CUSTOMER",
        first_name="Bertrand", last_name="Kamdem",
    )
    authed(outsider)
    assert api.get(f"/api/v1/projects/{project.pk}/evidences/").status_code in {403, 404}


def test_offline_sync_is_idempotent(api, authed, manager, project):
    """Le terrain renvoie le même lot deux fois : aucune preuve en double."""
    asset = make_asset(manager)
    payload = {
        "items": [
            {
                "project": project.pk,
                "kind": "PHOTO",
                "asset": asset.pk,
                "client_uuid": "0b0d4f2e-8f4b-4f7a-9c1e-2f5a6b7c8d90",
                "title": "Dalle du rez-de-chaussée",
                "is_offline_capture": True,
                "captured_at": "2026-09-27T16:40:00Z",
            }
        ]
    }
    authed(manager)
    first = api.post("/api/v1/evidences/sync/", payload, format="json")
    assert first.status_code == 200, first.content
    assert first.json()["created"] == 1

    replay = api.post("/api/v1/evidences/sync/", payload, format="json")
    assert replay.status_code == 200
    assert replay.json()["created"] == 0
    assert replay.json()["replayed"] == 1

    from apps.evidences.models import Evidence

    assert Evidence.objects.filter(project=project, title="Dalle du rez-de-chaussée").count() == 1


def test_pending_count_helps_the_team_triage(api, authed, manager, admin_user, project):
    asset = make_asset(manager)
    authed(manager)
    api.post(
        f"/api/v1/projects/{project.pk}/evidences/",
        {"project": project.pk, "kind": "PHOTO", "asset": asset.pk},
        format="json",
    )
    authed(admin_user)
    response = api.get(f"/api/v1/projects/{project.pk}/evidences/pending-count/")
    assert response.status_code == 200
    assert response.json()["pending"] >= 1
    assert Decimal(str(response.json().get("pending", 0))) >= 1


def test_evidence_can_carry_field_measurements(api, authed, manager, project):
    asset = make_asset(manager)
    authed(manager)
    created = api.post(
        f"/api/v1/projects/{project.pk}/evidences/",
        {
            "project": project.pk,
            "kind": "PHOTO",
            "asset": asset.pk,
            "title": "Ferraillage poteaux",
            "measurements": {"acier": "12 mm", "espacement": "20 cm", "longueur": "3,20 m"},
        },
        format="json",
    )
    assert created.status_code == 201, created.content
    assert created.json()["measurements"]["acier"] == "12 mm"
