"""Comptes KEMTA : le numéro de téléphone est l'identité principale.

Aucune inscription ne dépend d'une adresse e-mail : c'est une exigence produit
forte (marché camerounais + diaspora). L'e-mail reste optionnel et sert
uniquement aux notifications, factures et à la récupération secondaire.
"""
from __future__ import annotations

import secrets

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

from common.utils import mask_phone


class Role(models.TextChoices):
    """Rôles applicatifs. Un utilisateur a un rôle principal (RBAC simple)."""

    ADMIN = "ADMIN", "Administrateur KEMTA"
    MANAGER = "MANAGER", "Chargé de suivi KEMTA"
    FIELD = "FIELD", "Technicien terrain KEMTA"
    CUSTOMER = "CUSTOMER", "Client / propriétaire"
    COMPANY = "COMPANY", "Entreprise BTP"


class OTPPurpose(models.TextChoices):
    REGISTER = "REGISTER", "Inscription"
    LOGIN = "LOGIN", "Connexion"
    PASSWORD_RESET = "PASSWORD_RESET", "Réinitialisation du mot de passe"
    PHONE_CHANGE = "PHONE_CHANGE", "Changement de numéro"
    SENSITIVE_ACTION = "SENSITIVE_ACTION", "Action sensible"


class UserManager(BaseUserManager):
    """Gestionnaire d'utilisateurs basé sur le téléphone."""

    use_in_migrations = True

    def _create_user(self, phone: str, password: str | None, **extra):
        from common.utils import normalize_phone

        if not phone:
            raise ValueError("Le numéro de téléphone est obligatoire.")
        normalized = normalize_phone(phone, extra.pop("default_country", "CM"))
        user = self.model(phone=normalized, **extra)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.full_clean(exclude=["password"], validate_unique=False)
        user.save(using=self._db)
        return user

    def create_user(self, phone: str, password: str | None = None, **extra):
        extra.setdefault("role", Role.CUSTOMER)
        return self._create_user(phone, password, **extra)

    def create_superuser(self, phone: str, password: str, **extra):
        extra.update(is_staff=True, is_superuser=True, role=Role.ADMIN, phone_verified=True)
        return self._create_user(phone, password, **extra)

    def get_by_phone(self, phone: str, default_country: str = "CM"):
        from common.utils import normalize_phone

        return self.filter(phone=normalize_phone(phone, default_country)).first()


class User(AbstractBaseUser, PermissionsMixin):
    """Utilisateur KEMTA (client, entreprise, équipe KEMTA ou administrateur)."""

    phone = models.CharField(
        "téléphone",
        max_length=20,
        unique=True,
        db_index=True,
        help_text="Format international E.164, ex. +237699112233",
    )
    phone_verified = models.BooleanField("téléphone vérifié", default=False)
    first_name = models.CharField("prénom", max_length=80)
    last_name = models.CharField("nom", max_length=80)
    email = models.EmailField(
        "e-mail (facultatif)", blank=True, null=True, unique=True, db_index=True,
        help_text="Optionnel : sert aux notifications et aux factures.",
    )
    country = models.CharField("pays", max_length=2, blank=True, default="CM")
    city = models.CharField("ville", max_length=120, blank=True)
    role = models.CharField("rôle", max_length=20, choices=Role.choices, default=Role.CUSTOMER)
    avatar = models.ForeignKey(
        "common.Asset", verbose_name="photo de profil", null=True, blank=True, on_delete=models.SET_NULL
    )
    preferred_locale = models.CharField("langue", max_length=5, default="fr")
    is_active = models.BooleanField("actif", default=True)
    is_staff = models.BooleanField("accès administration", default=False)
    terms_accepted_at = models.DateTimeField("CGU acceptées le", null=True, blank=True)
    marketing_opt_in = models.BooleanField("accepte les informations KEMTA", default=True)
    last_seen_at = models.DateTimeField("dernière activité", null=True, blank=True)
    created_at = models.DateTimeField("créé le", auto_now_add=True)
    updated_at = models.DateTimeField("mis à jour le", auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        verbose_name = "utilisateur"
        verbose_name_plural = "utilisateurs"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("role", "is_active")),
            models.Index(fields=("-created_at",)),
        ]

    def __str__(self) -> str:
        return f"{self.full_name} ({mask_phone(self.phone)})"

    def save(self, *args, **kwargs) -> None:
        if self.email == "":
            self.email = None
        super().save(*args, **kwargs)

    # -- Identité ---------------------------------------------------------
    @property
    def full_name(self) -> str:
        name = f"{self.first_name} {self.last_name}".strip()
        return name or self.phone

    @property
    def short_name(self) -> str:
        return self.first_name or self.last_name or self.phone[-4:]

    @property
    def initials(self) -> str:
        return f"{(self.first_name or ' ')[:1]}{(self.last_name or ' ')[:1]}".strip().upper() or "K"

    @property
    def is_kemta_admin(self) -> bool:
        return self.role == Role.ADMIN or self.is_superuser

    @property
    def is_kemta_team(self) -> bool:
        return self.role in {Role.ADMIN, Role.MANAGER, Role.FIELD} or self.is_superuser or self.is_staff

    @property
    def is_customer(self) -> bool:
        return self.role == Role.CUSTOMER

    @property
    def is_company_user(self) -> bool:
        return self.role == Role.COMPANY

    @property
    def primary_company(self):
        """Entreprise dont l'utilisateur est propriétaire (une seule en pratique)."""
        membership = (
            self.company_memberships.select_related("company")
            .filter(role="OWNER")
            .order_by("-company__verification_status", "id")
            .first()
        )
        return membership.company if membership else None

    def touch(self) -> None:
        User.objects.filter(pk=self.pk).update(last_seen_at=timezone.now())


class PhoneVerification(models.Model):
    """Historique des vérifications de numéro (traçabilité anti-fraude)."""

    phone = models.CharField("téléphone", max_length=20, db_index=True)
    purpose = models.CharField("objet", max_length=20, choices=OTPPurpose.choices)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="phone_verifications")
    verified_at = models.DateTimeField("vérifié le", auto_now_add=True)
    ip_address = models.GenericIPAddressField("adresse IP", null=True, blank=True)

    class Meta:
        verbose_name = "vérification téléphone"
        verbose_name_plural = "vérifications téléphone"
        ordering = ("-verified_at",)

    def __str__(self) -> str:
        return f"{mask_phone(self.phone)} — {self.get_purpose_display()}"


class OTPVerification(models.Model):
    """Code OTP à usage unique.

    Le code n'est JAMAIS stocké en clair : on conserve une empreinte HMAC
    (clé secrète serveur + sel aléatoire par enregistrement), comparée en temps
    constant. L'expiration est courte (5 min par défaut), les tentatives sont
    limitées, et tout nouveau code invalide le précédent.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="utilisateur", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="otp_codes",
        help_text="Renseigné lorsque le code concerne un compte existant.",
    )
    phone = models.CharField("téléphone", max_length=20, db_index=True)
    purpose = models.CharField("objet", max_length=20, choices=OTPPurpose.choices, db_index=True)
    code_hash = models.CharField("empreinte du code", max_length=128)
    salt = models.CharField("sel", max_length=32)
    expires_at = models.DateTimeField("expire le", db_index=True)
    attempts = models.PositiveSmallIntegerField("tentatives", default=0)
    max_attempts = models.PositiveSmallIntegerField("tentatives maximales", default=5)
    resend_count = models.PositiveSmallIntegerField("renvois", default=0)
    used_at = models.DateTimeField("utilisé le", null=True, blank=True)
    invalidated_at = models.DateTimeField("invalidé le", null=True, blank=True)
    ip_address = models.GenericIPAddressField("adresse IP", null=True, blank=True)
    user_agent = models.CharField("agent utilisateur", max_length=255, blank=True)
    created_at = models.DateTimeField("créé le", auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "code OTP"
        verbose_name_plural = "codes OTP"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("phone", "purpose", "-created_at")),
            models.Index(fields=("expires_at", "used_at")),
        ]

    def __str__(self) -> str:
        return f"{mask_phone(self.phone)} — {self.get_purpose_display()} ({self.status_label})"

    # -- Cycle de vie -----------------------------------------------------
    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    @property
    def is_usable(self) -> bool:
        return (
            self.used_at is None
            and self.invalidated_at is None
            and not self.is_expired
            and self.attempts < self.max_attempts
        )

    @property
    def status_label(self) -> str:
        if self.used_at:
            return "utilisé"
        if self.invalidated_at:
            return "invalidé"
        if self.is_expired:
            return "expiré"
        if self.attempts >= self.max_attempts:
            return "trop de tentatives"
        return "actif"

    @property
    def seconds_remaining(self) -> int:
        return max(0, int((self.expires_at - timezone.now()).total_seconds()))

    # -- Empreinte --------------------------------------------------------
    def set_code(self, code: str) -> None:
        from apps.accounts.services.otp import hash_code

        self.salt = secrets.token_hex(8)
        self.code_hash = hash_code(code, self.salt)

    def matches(self, code: str) -> bool:
        from apps.accounts.services.otp import verify_code

        return verify_code(code, self.salt, self.code_hash)

    def register_failure(self) -> None:
        OTPVerification.objects.filter(pk=self.pk).update(attempts=models.F("attempts") + 1)
        self.attempts += 1

    def consume(self) -> None:
        OTPVerification.objects.filter(pk=self.pk).update(used_at=timezone.now())

    def invalidate(self) -> None:
        OTPVerification.objects.filter(pk=self.pk).update(invalidated_at=timezone.now())

    @classmethod
    def invalidate_active(cls, phone: str, purpose: str) -> int:
        """Invalide les codes encore valides (un seul code actif par usage)."""
        return cls.objects.filter(
            phone=phone, purpose=purpose, used_at__isnull=True, invalidated_at__isnull=True
        ).update(invalidated_at=timezone.now())


class Permission(models.Model):
    """Permission atomique de la plateforme (catalogue `common.permission_codes`)."""

    code = models.CharField("code", max_length=64, unique=True)
    label = models.CharField("libellé", max_length=160)
    category = models.CharField("catégorie", max_length=64, blank=True)
    description = models.CharField("description", max_length=255, blank=True)

    class Meta:
        verbose_name = "permission"
        verbose_name_plural = "permissions"
        ordering = ("category", "code")

    def __str__(self) -> str:
        return self.code


class RolePermission(models.Model):
    """Association rôle ↔ permission (RBAC pilotable depuis l'administration)."""

    role = models.CharField("rôle", max_length=20, choices=Role.choices)
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name="roles")
    allowed = models.BooleanField("autorisée", default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "permission de rôle"
        verbose_name_plural = "permissions de rôle"
        constraints = [
            models.UniqueConstraint(fields=("role", "permission"), name="uniq_role_permission"),
        ]
        indexes = [models.Index(fields=("role", "allowed"))]

    def __str__(self) -> str:
        state = "autorisée" if self.allowed else "refusée"
        return f"{self.get_role_display()} — {self.permission.code} ({state})"


class AuthAuditLog(models.Model):
    """Journal d'authentification : sécurité et conformité (jamais de secret)."""

    class Event(models.TextChoices):
        OTP_REQUESTED = "OTP_REQUESTED", "Code demandé"
        OTP_VERIFIED = "OTP_VERIFIED", "Code validé"
        OTP_FAILED = "OTP_FAILED", "Code invalide"
        OTP_EXPIRED = "OTP_EXPIRED", "Code expiré"
        OTP_THROTTLED = "OTP_THROTTLED", "Demande limitée"
        REGISTERED = "REGISTERED", "Compte créé"
        LOGIN_SUCCESS = "LOGIN_SUCCESS", "Connexion réussie"
        LOGIN_FAILED = "LOGIN_FAILED", "Connexion échouée"
        LOGOUT = "LOGOUT", "Déconnexion"
        TOKEN_REFRESH = "TOKEN_REFRESH", "Jeton renouvelé"
        PASSWORD_RESET_REQUESTED = "PASSWORD_RESET_REQUESTED", "Réinitialisation demandée"
        PASSWORD_RESET_DONE = "PASSWORD_RESET_DONE", "Mot de passe réinitialisé"
        PASSWORD_CHANGED = "PASSWORD_CHANGED", "Mot de passe modifié"
        ACCOUNT_LOCKED = "ACCOUNT_LOCKED", "Compte suspendu"
        PHONE_CHANGED = "PHONE_CHANGED", "Numéro modifié"

    phone = models.CharField("téléphone", max_length=20, blank=True, db_index=True)
    user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="auth_events"
    )
    event = models.CharField("événement", max_length=32, choices=Event.choices, db_index=True)
    success = models.BooleanField("succès", default=True)
    ip_address = models.GenericIPAddressField("adresse IP", null=True, blank=True)
    user_agent = models.CharField("agent utilisateur", max_length=255, blank=True)
    detail = models.CharField("détail", max_length=255, blank=True)
    created_at = models.DateTimeField("créé le", auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "journal d'authentification"
        verbose_name_plural = "journaux d'authentification"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("event", "-created_at")),
            models.Index(fields=("phone", "-created_at")),
        ]

    def __str__(self) -> str:
        return f"{self.get_event_display()} — {mask_phone(self.phone)}"


class DeviceSession(models.Model):
    """Session d'appareil : permet la révocation ciblée d'un refresh token."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sessions")
    jti = models.CharField("identifiant du jeton", max_length=64, unique=True)
    device_label = models.CharField("appareil", max_length=160, blank=True)
    ip_address = models.GenericIPAddressField("adresse IP", null=True, blank=True)
    user_agent = models.CharField("agent utilisateur", max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField("dernière utilisation", auto_now=True)
    expires_at = models.DateTimeField("expire le")
    revoked_at = models.DateTimeField("révoquée le", null=True, blank=True)

    class Meta:
        verbose_name = "session d'appareil"
        verbose_name_plural = "sessions d'appareil"
        ordering = ("-last_used_at",)
        indexes = [models.Index(fields=("user", "-last_used_at"))]

    def __str__(self) -> str:
        return f"{self.user_id} — {self.device_label or self.jti[:8]}"

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None and self.expires_at > timezone.now()
