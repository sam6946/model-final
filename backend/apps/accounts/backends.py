"""Backends d'authentification : le téléphone remplace le couple username/login."""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

from common.utils import normalize_phone


class PhonePasswordBackend(ModelBackend):
    """Authentifie par numéro de téléphone + mot de passe.

    Messages d'erreur volontairement génériques : on ne révèle jamais si un
    numéro existe (protection contre l'énumération de comptes).
    """

    def authenticate(self, request, username=None, password=None, phone=None, **kwargs):
        raw_phone = phone or username or kwargs.get("identifier")
        if not raw_phone or not password:
            return None
        UserModel = get_user_model()
        try:
            normalized = normalize_phone(str(raw_phone))
        except ValueError:
            return None
        for candidate in {normalized, normalized.lstrip("+")}:
            try:
                user = UserModel._default_manager.get(phone=candidate)
            except UserModel.DoesNotExist:
                continue
            except UserModel.MultipleObjectsReturned:  # pragma: no cover
                user = UserModel._default_manager.filter(phone=candidate).order_by("id").first()
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
        # Consommation de temps comparable pour limiter les attaques temporelles.
        UserModel().set_password(password)
        return None

    def user_can_authenticate(self, user) -> bool:
        return bool(user.is_active)
