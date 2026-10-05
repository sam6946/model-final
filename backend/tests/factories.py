"""Fabriques de test : objets métier cohérents avec le modèle KEMTA.

On construit les objets par l'ORM (et non par l'API) pour que chaque test
n'ait à décrire que ce qu'il vérifie réellement.
"""
from __future__ import annotations

import itertools
from datetime import date, timedelta

from django.utils import timezone
from decimal import Decimal

from apps.companies.models import Company, CompanyMember, VerificationStatus
from apps.opportunities.models import Opportunity, OpportunityStatus, OpportunityVisibility
from apps.projects.models import HealthStatus, Project, ProjectKind, ProjectStatus
from common.models import Asset, AssetKind, AssetStatus

_counter = itertools.count(1000)


def _n() -> int:
    return next(_counter)


def make_asset(user, *, kind: str = AssetKind.IMAGE, public: bool = False) -> Asset:
    n = _n()
    return Asset.objects.create(
        kind=kind,
        status=AssetStatus.READY,
        bucket="local",
        key=f"tests/asset-{n}.jpg",
        original_filename=f"photo-{n}.jpg",
        mime_type="image/jpeg",
        size_bytes=182_400,
        uploaded_by=user,
        is_public=public,
    )


def make_avatar(user) -> Asset:
    asset = make_asset(user, public=True)
    user.avatar = asset
    user.save(update_fields=["avatar"])
    return asset


def make_project(
    customer,
    *,
    manager=None,
    company=None,
    kind: str = ProjectKind.FOLLOW_UP,
    name: str = "",
    budget: int = 25_000_000,
    spent: int = 0,
    progress: str = "35.00",
    status: str = ProjectStatus.IN_PROGRESS,
    health: str = HealthStatus.ON_TRACK,
    planned_end: date | None = None,
) -> Project:
    n = _n()
    return Project.objects.create(
        reference=f"KEMTA-PRJ-2026-{n:05d}",
        name=name or f"Villa familiale {n}",
        slug=f"villa-familiale-{n}",
        kind=kind,
        customer=customer,
        manager=manager,
        company=company,
        location_text="Bafoussam, quartier Administratif",
        description="Construction d'une villa de 4 chambres avec suivi photo hebdomadaire.",
        status=status,
        health=health,
        physical_progress=Decimal(progress),
        budget_total_xaf=Decimal(budget),
        budget_spent_xaf=Decimal(spent),
        planned_start=date.today() - timedelta(days=120),
        planned_end=planned_end or date.today() + timedelta(days=90),
    )


def make_company(user, *, verified: bool = True, published: bool = True, name: str = "") -> Company:
    n = _n()
    company = Company.objects.create(
        name=name or f"Bâtisseurs de l'Ouest {n}",
        legal_name=name or f"Bâtisseurs de l'Ouest {n} SARL",
        owner=user,
        city="Bafoussam",
        region="OU",
        description=(
            "Entreprise générale de bâtiment : gros œuvre, second œuvre et finitions "
            "de villas et d'immeubles, avec suivi de chantier documenté."
        ),
        years_experience=7,
        employees_count=18,
        projects_count=23,
        verification_status=(
            VerificationStatus.VERIFIED if verified else VerificationStatus.PENDING
        ),
        is_published=published,
    )
    CompanyMember.objects.create(
        company=company, user=user, role=CompanyMember.MemberRole.OWNER, job_title="Gérant"
    )
    return company


def make_opportunity(
    *,
    created_by=None,
    title: str = "Construction d'une villa R+1 à Bafoussam",
    status: str = OpportunityStatus.OPEN,
    visibility: str = OpportunityVisibility.PUBLIC,
    days_left: int = 21,
    requires_verified: bool = True,
    budget_min: int = 40_000_000,
    budget_max: int = 55_000_000,
) -> Opportunity:
    n = _n()
    if created_by is None:
        from apps.accounts.models import Role, User

        created_by = User.objects.create_user(
            phone=f"+23769{next(_counter):07d}",
            password="Kemta!2026test",
            first_name="Pilote",
            last_name="Marchés",
            role=Role.MANAGER,
        )
    return Opportunity.objects.create(
        reference=f"KEMTA-OPP-2026-{n:05d}",
        title=title,
        slug=f"villa-r1-bafoussam-{n}",
        description=(
            "Le client souhaite construire une villa R+1 de 260 m² avec sous-sol "
            "semi-enterré, sur un terrain viabilisé du quartier Administratif."
        ),
        scope_of_work="Terrassement, fondations, gros œuvre, toiture, second œuvre et finitions.",
        location_text="Bafoussam, quartier Administratif",
        budget_min_xaf=Decimal(budget_min),
        budget_max_xaf=Decimal(budget_max),
        application_deadline=date.today() + timedelta(days=days_left),
        published_at=timezone.now() if status in {"OPEN", "REVIEWING"} else None,
        requires_verified_company=requires_verified,
        status=status,
        visibility=visibility,
        is_featured=True,
        created_by=created_by,
    )
