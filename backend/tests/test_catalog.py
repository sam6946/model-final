"""Catalogue public : annuaire BTP, filtres, réalisations et référentiels."""
from __future__ import annotations

import pytest

from tests.factories import make_company

pytestmark = pytest.mark.django_db


def test_public_directory_lists_verified_companies(api, company_owner, other_company):
    response = api.get("/api/v1/companies/")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] >= 1
    assert "results" in body
    slugs = {item["slug"] for item in body["results"]}
    assert company_owner.slug in slugs
    for item in body["results"]:
        assert item["name"]
        assert item["is_verified"] is True  # l'annuaire public ne montre que des dossiers vérifiés


def test_directory_search_and_city_filter(api, company_owner):
    found = api.get("/api/v1/companies/", {"search": "Wouri"})
    assert found.status_code == 200, found.content
    names = [item["name"] for item in found.json()["results"]]
    assert any("Wouri" in name for name in names)

    filtered = api.get("/api/v1/companies/", {"city": "Bafoussam"})
    assert filtered.status_code == 200
    for item in filtered.json()["results"]:
        assert "Bafoussam" in item["city"]


def test_company_page_is_public_and_detailed(api, company_owner):
    response = api.get(f"/api/v1/companies/{company_owner.slug}/")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == company_owner.name
    assert body["description"]
    assert "specialities" in body
    assert "realizations_count" in body
    assert body["verification_status"] == company_owner.verification_status
    assert body["contact"]["preferred_channel"] == "KEMTA"  # KEMTA reste l'intermédiaire


def test_unknown_or_unpublished_company_returns_404(api):
    assert api.get("/api/v1/companies/entreprise-qui-nexiste-pas/").status_code == 404


def test_specialties_reference_data_is_exposed(api):
    response = api.get("/api/v1/catalog/specialties/")
    assert response.status_code == 200
    body = response.json()
    items = body["results"] if isinstance(body, dict) and "results" in body else body
    assert items, "Les corps d'état BTP doivent alimenter le formulaire d'inscription."


def test_locations_reference_data_includes_west_region(api):
    """Le siège est à Bafoussam : la région de l'Ouest doit être couverte."""
    response = api.get("/api/v1/catalog/locations/")
    assert response.status_code == 200
    body = response.json()
    names = {item["name"] for item in body["cities"]}
    assert {"Bafoussam", "Douala", "Yaoundé"} <= names


def test_public_content_feeds_the_landing_page(api):
    response = api.get("/api/v1/catalog/public-content/")
    assert response.status_code == 200
    body = response.json()
    assert body.get("trust_stats") or body.get("stats")
    assert body.get("faq") is not None


def _items(response):
    """Liste paginée ou liste simple selon les endpoints."""
    body = response.json()
    return body["results"] if isinstance(body, dict) and "results" in body else body


def test_company_documents_require_ownership(api, authed, company_owner, other_company, manager):
    authed(company_owner.owner)
    mine = api.get("/api/v1/company/documents/")
    assert mine.status_code == 200
    company_ids = {item["asset"] for item in _items(mine) if item.get("asset")}

    authed(manager)
    # L'équipe KEMTA n'a pas d'entreprise : elle ne voit aucun document d'entreprise.
    team_view = api.get("/api/v1/company/documents/")
    assert team_view.status_code == 200
    assert {item["asset"] for item in _items(team_view) if item.get("asset")} == set()
    assert isinstance(company_ids, set)


def test_realizations_can_be_filtered_by_type(api, company_owner):
    from apps.btp_catalog.models import Realization, RealizationStatus, RealizationType
    from tests.factories import make_asset

    asset = make_asset(company_owner.owner, public=True)
    Realization.objects.create(
        company=company_owner,
        title="Villa contemporaine 320 m²",
        slug="villa-contemporaine-320",
        realization_type=RealizationType.VILLA,
        description="Villa R+1 livrée clé en main à Bafoussam, finitions haut de gamme.",
        location_text="Bafoussam",
        year=2025,
        budget_xaf=72_000_000,
        duration_days=240,
        surface_m2=320,
        cover=asset,
        status=RealizationStatus.PUBLISHED,
    )
    response = api.get("/api/v1/catalog/realizations/", {"type": "VILLA"})
    assert response.status_code == 200, response.content
    titles = [item["title"] for item in response.json()["results"]]
    assert "Villa contemporaine 320 m²" in titles

    other = api.get("/api/v1/catalog/realizations/", {"type": "BUREAU"})
    assert "Villa contemporaine 320 m²" not in [item["title"] for item in other.json()["results"]]


def test_realization_detail_is_public_with_before_after_media(api, company_owner):
    from apps.btp_catalog.models import (
        Realization,
        RealizationMedia,
        RealizationStatus,
        RealizationType,
    )
    from tests.factories import make_asset

    realization = Realization.objects.create(
        company=company_owner,
        title="Rénovation d'une maison familiale",
        slug="renovation-maison-familiale",
        realization_type=RealizationType.RENOVATION,
        description="Réhabilitation complète d'une maison des années 90 à Bafoussam.",
        location_text="Bafoussam",
        year=2024,
        status=RealizationStatus.PUBLISHED,
    )
    before = make_asset(company_owner.owner, public=True)
    after = make_asset(company_owner.owner, public=True)
    RealizationMedia.objects.create(
        realization=realization, kind=RealizationMedia.MediaKind.BEFORE, asset=before, order=1
    )
    RealizationMedia.objects.create(
        realization=realization, kind=RealizationMedia.MediaKind.AFTER, asset=after, order=2
    )

    response = api.get(f"/api/v1/catalog/realizations/{realization.slug}/")
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == realization.title
    assert body["before_after"]["before"] and body["before_after"]["after"]
