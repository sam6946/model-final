"""Contrôle d'accès KEMTA : RBAC par rôle/périmètre + objets.

Règles fortes :
- le backend vérifie TOUJOURS les permissions (le masquage front n'est qu'UX) ;
- les permissions effectives d'un utilisateur sont calculées une fois puis
  mises en cache Redis (TTL court), car elles changent rarement ;
- l'accès à un objet (projet, entreprise) est vérifié via l'adhésion, jamais
  via un ``id`` deviné dans l'URL.
"""
from __future__ import annotations

from rest_framework.permissions import SAFE_METHODS, BasePermission

from common.cache import TTL, make_key
from common.permission_codes import Perm
from django.core.cache import cache


def get_user_permissions(user) -> set[str]:
    """Permissions effectives (cache Redis 10 min, invalidé à la modification).

    Seul un superutilisateur court-circuite le RBAC. ``is_staff`` donne accès à
    l'admin Django, PAS toutes les permissions de l'API : sans cette
    distinction, un chargé de suivi marqué « staff » hériterait de la
    facturation et des journaux d'audit (élévation de privilèges).

    Le rôle ADMIN, lui, reçoit bien toutes les permissions côté API.
    """
    if not user or not user.is_authenticated:
        return set()
    if user.is_superuser:
        from common.permission_codes import ALL_PERMISSIONS

        return set(ALL_PERMISSIONS.keys())
    key = make_key("permissions", user.pk, user.role)
    cached = cache.get(key)
    if cached is not None:
        return set(cached)
    from apps.accounts.models import RolePermission

    codes = set(
        RolePermission.objects.filter(role=user.role, allowed=True)
        .exclude(permission__code="")
        .values_list("permission__code", flat=True)
    )
    cache.set(key, sorted(codes), TTL["permissions"])
    return codes


def clear_user_permissions(user) -> None:
    cache.delete(make_key("permissions", user.pk, user.role))


class HasPermission(BasePermission):
    """``permission_classes = [HasPermission(Perm.MANAGE_PROJECT)]``."""

    def __init__(self, *codes: str, any_of: bool = False) -> None:
        self.codes = codes
        self.any_of = any_of

    def __call__(self) -> "HasPermission":  # DRF instancie sans argument si besoin
        return self

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        effective = get_user_permissions(user)
        if self.any_of:
            return any(code in effective for code in self.codes)
        return all(code in effective for code in self.codes)


class IsAdminRole(BasePermission):
    """Réservé aux administrateurs KEMTA (rôle ADMIN ou compte staff)."""

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and (user.is_staff or user.is_kemta_admin))


class IsKemtaTeam(BasePermission):
    """Équipe KEMTA : administration et chargés de suivi."""

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and user.is_kemta_team)


class IsCompanyOwner(BasePermission):
    """L'utilisateur possède ou administre au moins une entreprise BTP."""

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not (user and user.is_authenticated):
            return False
        return user.company_memberships.filter(role__in=("OWNER", "MANAGER")).exists()


class IsOwnerOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj) -> bool:
        if request.method in SAFE_METHODS:
            return True
        owner_field = getattr(view, "owner_field", "owner")
        return getattr(obj, owner_field, None) == request.user


class IsProjectMember(BasePermission):
    """Accès en lecture à un projet : client, membre d'équipe, société affectée."""

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        if user.is_kemta_team:
            return True
        if obj.customer_id == user.id:
            return True
        if obj.members.filter(user=user).exists():
            return True
        company = getattr(user, "primary_company", None)
        return bool(company and obj.company_id == company.id)


class CanManageProject(BasePermission):
    """Écriture sur le chantier : manager KEMTA, entreprise affectée, manager projet."""

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        if user.is_kemta_team:
            return True
        if obj.manager_id == user.id:
            return True
        if obj.members.filter(user=user, role__in=("MANAGER", "SUPERVISOR")).exists():
            return True
        company = getattr(user, "primary_company", None)
        return bool(company and obj.company_id == company.id)


class CanViewFinance(BasePermission):
    """Finances projet : client (transparence), manager, équipe KEMTA."""

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        if user.is_kemta_team or obj.customer_id == user.id or obj.manager_id == user.id:
            return True
        return obj.members.filter(user=user, role__in=("MANAGER", "SUPERVISOR")).exists()


def user_can_manage_project_finance(user, project) -> bool:
    if not (user and user.is_authenticated):
        return False
    if user.is_kemta_team or project.manager_id == user.id or project.customer_id == user.id:
        return True
    if project.members.filter(user=user, role__in=("MANAGER", "SUPERVISOR")).exists():
        return True
    return Perm.MANAGE_FINANCE in get_user_permissions(user)
