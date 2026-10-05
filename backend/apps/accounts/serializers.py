"""Serializers d'authentification : validation stricte + messages humains.

Toutes les erreurs sont formulées pour un utilisateur final (le formulaire les
affiche telles quelles) : « Veuillez renseigner votre numéro de téléphone. »
"""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import (
    AuthAuditLog,
    DeviceSession,
    OTPPurpose,
    PhoneVerification,
    Role,
    User,
)
from common.utils import format_phone_display, normalize_phone

UserModel = get_user_model()


class PhoneField(serializers.CharField):
    """Champ téléphone : normalisé en E.164 avec message d'erreur pédagogique."""

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("max_length", 24)
        kwargs.setdefault("error_messages", {
            "blank": "Veuillez renseigner votre numéro de téléphone.",
            "required": "Veuillez renseigner votre numéro de téléphone.",
        })
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        raw = super().to_internal_value(data)
        try:
            return normalize_phone(str(raw))
        except ValueError as exc:
            raise serializers.ValidationError(
                str(exc) if str(exc) and "doit contenir" in str(exc)
                else "Ce numéro de téléphone n'est pas valide. Exemple : +237 6 99 11 22 33."
            ) from exc


class PasswordField(serializers.CharField):
    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("write_only", True)
        kwargs.setdefault("style", {"input_type": "password"})
        kwargs.setdefault("max_length", 128)
        kwargs.setdefault("error_messages", {
            "blank": "Veuillez saisir votre mot de passe.",
            "required": "Veuillez saisir votre mot de passe.",
        })
        super().__init__(**kwargs)


class UserSummarySerializer(serializers.ModelSerializer):
    """Identité minimale, utilisée partout où on affiche une personne."""

    full_name = serializers.CharField(read_only=True)
    initials = serializers.CharField(read_only=True)
    phone_display = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    company = serializers.SerializerMethodField()

    class Meta:
        model = UserModel
        fields = (
            "id", "phone", "phone_display", "phone_verified", "first_name", "last_name",
            "full_name", "initials", "email", "city", "country", "role", "avatar_url",
            "company", "created_at",
        )

    def get_phone_display(self, obj: User) -> str:
        return format_phone_display(obj.phone)

    def get_avatar_url(self, obj: User) -> str:
        return obj.avatar.thumbnail_url if obj.avatar_id else ""

    def get_company(self, obj: User) -> dict | None:
        company = getattr(obj, "_prefetched_company", None) or obj.primary_company
        if not company:
            return None
        return {
            "id": company.id,
            "name": company.name,
            "slug": company.slug,
            "verification_status": company.verification_status,
        }


class UserProfileSerializer(UserSummarySerializer):
    class Meta(UserSummarySerializer.Meta):
        fields = UserSummarySerializer.Meta.fields + ("preferred_locale", "marketing_opt_in", "last_seen_at")
        read_only_fields = ("phone", "role", "phone_verified", "last_seen_at")


class OTPRequestSerializer(serializers.Serializer):
    phone = PhoneField()
    purpose = serializers.ChoiceField(
        choices=[
            (OTPPurpose.REGISTER, "Inscription"),
            (OTPPurpose.LOGIN, "Connexion"),
            (OTPPurpose.PASSWORD_RESET, "Réinitialisation du mot de passe"),
        ],
        default=OTPPurpose.REGISTER,
        error_messages={"invalid_choice": "Objet de vérification inconnu."},
    )

    def validate(self, attrs):
        purpose = attrs["purpose"]
        phone = attrs["phone"]
        exists = UserModel.objects.filter(phone=phone).exists()

        if purpose == OTPPurpose.REGISTER and exists:
            raise serializers.ValidationError({
                "phone": "Ce numéro est déjà associé à un compte KEMTA. Connectez-vous plutôt, "
                         "ou réinitialisez votre mot de passe si vous l'avez oublié."
            })
        if purpose == OTPPurpose.LOGIN and not exists:
            raise serializers.ValidationError({
                "phone": "Aucun compte KEMTA n'est associé à ce numéro. "
                         "Créez votre compte en quelques secondes."
            })
        if purpose == OTPPurpose.PASSWORD_RESET and not exists:
            # On ne révèle jamais l'existence d'un compte : message neutre.
            attrs["silent"] = True
        return attrs


class OTPVerifySerializer(serializers.Serializer):
    phone = PhoneField()
    code = serializers.CharField(
        min_length=4, max_length=8,
        error_messages={
            "blank": "Veuillez saisir le code reçu par SMS.",
            "required": "Veuillez saisir le code reçu par SMS.",
            "min_length": "Le code contient 6 chiffres.",
            "max_length": "Le code contient 6 chiffres.",
        },
    )
    purpose = serializers.ChoiceField(choices=OTPPurpose.choices, default=OTPPurpose.REGISTER)

    def validate_code(self, value: str) -> str:
        digits = "".join(ch for ch in str(value) if ch.isdigit())
        if digits != str(value).strip():
            raise serializers.ValidationError("Le code ne contient que des chiffres.")
        return digits


class RegisterSerializer(serializers.Serializer):
    """Création de compte après vérification du numéro par OTP."""

    phone = PhoneField()
    verification_ticket = serializers.CharField(
        error_messages={"blank": "Validez d'abord le code reçu par SMS.", "required": "Validez d'abord le code reçu par SMS."}
    )
    first_name = serializers.CharField(
        max_length=80, error_messages={"blank": "Veuillez renseigner votre prénom.", "required": "Veuillez renseigner votre prénom."}
    )
    last_name = serializers.CharField(
        max_length=80, error_messages={"blank": "Veuillez renseigner votre nom.", "required": "Veuillez renseigner votre nom."}
    )
    password = PasswordField()
    password_confirm = PasswordField()
    email = serializers.EmailField(
        required=False, allow_blank=True, allow_null=True,
        error_messages={"invalid": "Cette adresse e-mail ne semble pas valide."},
    )
    country = serializers.CharField(max_length=2, required=False, default="CM")
    city = serializers.CharField(max_length=120, required=False, allow_blank=True)
    role = serializers.ChoiceField(
        choices=[(Role.CUSTOMER, "Client / propriétaire"), (Role.COMPANY, "Entreprise BTP")],
        default=Role.CUSTOMER,
    )
    terms_accepted = serializers.BooleanField(
        error_messages={"required": "Vous devez accepter les conditions d'utilisation pour créer votre compte."}
    )
    marketing_opt_in = serializers.BooleanField(required=False, default=True)

    def validate_first_name(self, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise serializers.ValidationError("Le prénom doit contenir au moins 2 caractères.")
        return cleaned

    def validate_last_name(self, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise serializers.ValidationError("Le nom doit contenir au moins 2 caractères.")
        return cleaned

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Les deux mots de passe ne correspondent pas."})
        if not attrs.get("terms_accepted"):
            raise serializers.ValidationError({"terms_accepted": "Vous devez accepter les conditions d'utilisation."})
        if UserModel.objects.filter(phone=attrs["phone"]).exists():
            raise serializers.ValidationError({"phone": "Ce numéro est déjà associé à un compte KEMTA."})
        email = (attrs.get("email") or "").strip().lower() or None
        if email and UserModel.objects.filter(email__iexact=email).exists():
            # L'e-mail n'est pas bloquant : on l'écarte plutôt que de refuser
            # une inscription légitime.
            attrs["email"] = None
            attrs["email_conflict"] = True
        else:
            attrs["email"] = email
        # Validation du mot de passe par les règles Django (longueur, commun, numérique).
        try:
            validate_password(attrs["password"], user=UserModel(phone=attrs["phone"]))
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)}) from exc
        return attrs


class LoginSerializer(serializers.Serializer):
    """Connexion par téléphone + mot de passe (option principale)."""

    phone = PhoneField()
    password = PasswordField()

    def validate(self, attrs):
        from django.contrib.auth import authenticate

        user = authenticate(
            request=self.context.get("request"), phone=attrs["phone"], password=attrs["password"]
        )
        if user is None:
            raise serializers.ValidationError({
                "detail": "Numéro ou mot de passe incorrect. Vérifiez votre saisie ou "
                          "connectez-vous avec un code SMS."
            })
        if not user.is_active:
            raise serializers.ValidationError({
                "detail": "Votre compte est suspendu. Contactez le support KEMTA pour le réactiver."
            })
        attrs["user"] = user
        return attrs


class PasswordResetConfirmSerializer(serializers.Serializer):
    phone = PhoneField()
    verification_ticket = serializers.CharField(
        error_messages={"blank": "Validez d'abord le code reçu par SMS."}
    )
    password = PasswordField()
    password_confirm = PasswordField()

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Les deux mots de passe ne correspondent pas."})
        try:
            validate_password(attrs["password"])
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)}) from exc
        return attrs


class PasswordChangeSerializer(serializers.Serializer):
    current_password = PasswordField()
    password = PasswordField()
    password_confirm = PasswordField()

    def validate_current_password(self, value: str) -> str:
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Votre mot de passe actuel ne correspond pas.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Les deux mots de passe ne correspondent pas."})
        if attrs["current_password"] == attrs["password"]:
            raise serializers.ValidationError({"password": "Le nouveau mot de passe doit être différent de l'ancien."})
        try:
            validate_password(attrs["password"], user=self.context["request"].user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)}) from exc
        return attrs


class PhoneChangeSerializer(serializers.Serializer):
    """Demande de changement de numéro (l'ancien numéro reste maître)."""

    new_phone = PhoneField()

    def validate_new_phone(self, value: str) -> str:
        if UserModel.objects.filter(phone=value).exists():
            raise serializers.ValidationError("Ce numéro est déjà utilisé par un autre compte KEMTA.")
        return value


class PhoneChangeConfirmSerializer(serializers.Serializer):
    new_phone = PhoneField()
    code = serializers.CharField(min_length=4, max_length=8)


class DeviceSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceSession
        fields = ("id", "device_label", "ip_address", "created_at", "last_used_at", "expires_at", "revoked_at")


class AuthAuditLogSerializer(serializers.ModelSerializer):
    event_label = serializers.CharField(source="get_event_display", read_only=True)

    class Meta:
        model = AuthAuditLog
        fields = ("id", "event", "event_label", "success", "ip_address", "user_agent", "detail", "created_at")


class KemtaTokenObtainSerializer(TokenObtainPairSerializer):
    """Ajoute les informations utiles au frontend dans le jeton d'accès.

    Le frontend peut afficher le rôle sans appel réseau supplémentaire ; les
    permissions restent vérifiées côté serveur à chaque requête.
    """

    username_field = "phone"

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        token["name"] = user.full_name
        token["phone"] = user.phone
        token["verified"] = user.phone_verified
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UserSummarySerializer(self.user).data
        return data


class KemtaTokenRefreshSerializer(TokenRefreshSerializer):
    """Rotation avec révocation : un refresh volé devient inexploitable."""

    def validate(self, attrs):
        data = super().validate(attrs)
        from rest_framework_simplejwt.tokens import AccessToken, TokenError

        try:
            access = AccessToken(data["access"])
            user_id = access["user_id"]
        except (TokenError, KeyError):  # pragma: no cover
            return data
        DeviceSession.objects.filter(user_id=user_id, revoked_at__isnull=True).update(
            last_used_at=timezone.now()
        )
        return data


def issue_tokens_for_user(user, *, request=None, device_label: str = "") -> dict:
    """Émet une paire de jetons et enregistre la session d'appareil."""
    refresh = RefreshToken.for_user(user)
    refresh["role"] = user.role
    refresh["name"] = user.full_name

    expires_at = timezone.now() + refresh.access_token.lifetime
    ip = None
    user_agent = ""
    if request is not None:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        ip = (forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR")) or None
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:255]

    try:
        with transaction.atomic():
            DeviceSession.objects.create(
                user=user,
                jti=str(refresh["jti"])[:64],
                device_label=(device_label or user_agent)[:160],
                ip_address=ip,
                user_agent=user_agent,
                expires_at=expires_at,
            )
    except IntegrityError:  # pragma: no cover - collision improbable
        pass

    UserModel.objects.filter(pk=user.pk).update(last_seen_at=timezone.now())
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "expires_in": int(refresh.access_token.lifetime.total_seconds()),
        "refresh_expires_in": int(refresh.lifetime.total_seconds()),
        "token_type": "Bearer",
    }


def create_user_from_registration(*, data: dict, request=None) -> User:
    """Crée l'utilisateur après validation du ticket OTP (transaction unique)."""
    with transaction.atomic():
        user = UserModel.objects.create_user(
            phone=data["phone"],
            password=data["password"],
            first_name=data["first_name"].strip(),
            last_name=data["last_name"].strip(),
            email=data.get("email"),
            country=(data.get("country") or "CM")[:2].upper(),
            city=(data.get("city") or "").strip()[:120],
            role=data.get("role") or Role.CUSTOMER,
            phone_verified=True,
            marketing_opt_in=bool(data.get("marketing_opt_in", True)),
            terms_accepted_at=timezone.now(),
        )
        PhoneVerification.objects.create(
            phone=user.phone,
            purpose=OTPPurpose.REGISTER,
            user=user,
            ip_address=(request.META.get("REMOTE_ADDR") if request else None),
        )
    AuthAuditLog.objects.create(
        phone=user.phone,
        user=user,
        event=AuthAuditLog.Event.REGISTERED,
        ip_address=(request.META.get("REMOTE_ADDR") if request else None),
        user_agent=(request.META.get("HTTP_USER_AGENT", "")[:255] if request else ""),
        detail=f"role={user.role}",
    )
    return user
