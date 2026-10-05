"""Fixtures partagées de la suite de tests KEMTA.

Principes :
  · aucun accès réseau, aucun service externe : SMS et paiements sont simulés ;
  · les données de référence (plans, permissions, corps d'état, localisations)
    sont installées une fois par session via la commande `seed_kemta`, comme en
    production ;
  · chaque test obtient des utilisateurs isolés, avec des numéros uniques.
"""
from __future__ import annotations

import itertools

import pytest
from django.core.management import call_command
from django.test import Client as DjangoClient
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.companies.models import Company, CompanyMember, VerificationStatus

_counter = itertools.count(1)


def make_phone() -> str:
    """Numéro camerounais valide et unique (le format est vérifié par l'API)."""
    return f"+23765{next(_counter):07d}"


@pytest.fixture(scope="session")
def reference_data(django_db_setup, django_db_blocker):
    """Données de référence : plans, permissions, référentiels, contenus publics."""
    with django_db_blocker.unblock():
        call_command("seed_kemta", verbosity=0)


@pytest.fixture(autouse=True)
def clear_cache():
    """Le cache LocMem survit d'un test à l'autre : on l'isole systématiquement.

    Sans cela, un tableau de bord ou un catalogue mis en cache par un test
    fausserait le suivant (faux positifs et faux négatifs).
    """
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api() -> APIClient:
    return APIClient()


@pytest.fixture
def customer(db, reference_data) -> User:
    return User.objects.create_user(
        phone=make_phone(),
        password="Kemta!2026test",
        first_name="Aïcha",
        last_name="Mbarga",
        role=Role.CUSTOMER,
        city="Douala",
    )


@pytest.fixture
def manager(db, reference_data) -> User:
    user = User.objects.create_user(
        phone=make_phone(),
        password="Kemta!2026test",
        first_name="Clarisse",
        last_name="Etoundi",
        role=Role.MANAGER,
        city="Douala",
    )
    return user


@pytest.fixture
def admin_user(db, reference_data) -> User:
    return User.objects.create_user(
        phone=make_phone(),
        password="Kemta!2026test",
        first_name="Serge",
        last_name="Nkoulou",
        role=Role.ADMIN,
        is_staff=True,
        city="Douala",
    )


@pytest.fixture
def company_owner(db, reference_data):
    """Entreprise BTP vérifiée avec son dirigeant."""
    user = User.objects.create_user(
        phone=make_phone(),
        password="Kemta!2026test",
        first_name="Achille",
        last_name="Fotso",
        role=Role.COMPANY,
        city="Douala",
    )
    company = Company.objects.create(
        name="Bâtisseurs du Wouri SARL",
        legal_name="Bâtisseurs du Wouri SARL",
        owner=user,
        city="Douala",
        region="LT",
        description=(
            "Entreprise générale de bâtiment basée à Douala : gros œuvre, second œuvre et "
            "finitions pour villas et immeubles, avec un suivi de chantier documenté."
        ),
        years_experience=9,
        employees_count=24,
        projects_count=31,
        verification_status=VerificationStatus.VERIFIED,
        is_published=True,
    )
    CompanyMember.objects.create(company=company, user=user, role=CompanyMember.MemberRole.OWNER, job_title="Gérant")
    return company


@pytest.fixture
def other_company(db, reference_data):
    user = User.objects.create_user(
        phone=make_phone(),
        password="Kemta!2026test",
        first_name="Brice",
        last_name="Ngo",
        role=Role.COMPANY,
        city="Yaoundé",
    )
    company = Company.objects.create(
        name="Ngo Frères BTP",
        owner=user,
        city="Yaoundé",
        region="CE",
        description=(
            "Entreprise de travaux publics et de rénovation basée à Yaoundé, interventions sur "
            "voiries légères, forages et réhabilitation de bâtiments existants."
        ),
        verification_status=VerificationStatus.PENDING,
    )
    CompanyMember.objects.create(company=company, user=user, role=CompanyMember.MemberRole.OWNER)
    return company


def login(api: APIClient, phone: str, password: str = "Kemta!2026test") -> str:
    """Authentifie un client de test et renvoie le jeton d'accès."""
    response = api.post("/api/v1/auth/login/", {"phone": phone, "password": password}, format="json")
    assert response.status_code == 200, response.content
    token = response.json()["access"]
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return token


@pytest.fixture
def authed(api):
    """Fonction utilitaire : `authed(user)` connecte le client API."""

    def _auth(user, password: str = "Kemta!2026test"):
        login(api, user.phone, password)
        return api

    return _auth
