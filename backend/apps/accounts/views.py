"""Vues d'authentification KEMTA.

Parcours principal (téléphone d'abord, e-mail jamais obligatoire) :
1. POST /auth/otp/request/      → envoi d'un code par SMS
2. POST /auth/otp/verify/       → validation du code, renvoi d'un ticket
3. POST /auth/register/         → création du compte (téléphone vérifié)
   ou POST /auth/login/         → téléphone + mot de passe
   ou POST /auth/login/otp/verify/ → téléphone + code (connexion sans mot de passe)
4. POST /auth/password/reset/confirm/
"""
from __future__ import annotations

import logging
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import throttle_classes
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

from apps.accounts.models import AuthAuditLog, DeviceSession, OTPPurpose, Role
from apps.accounts.serializers import (
    AuthAuditLogSerializer,
    DeviceSessionSerializer,
    LoginSerializer,
    OTPRequestSerializer,
    OTPVerifySerializer,
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PhoneChangeConfirmSerializer,
    PhoneChangeSerializer,
    RegisterSerializer,
    UserProfileSerializer,
    UserSummarySerializer,
    create_user_from_registration,
    issue_tokens_for_user,
)
from apps.accounts.services import otp as otp_service
from common.exceptions import BusinessRuleError
from common.permissions import get_user_permissions
from common.throttling import (
    LoginThrottle,
    OTPRequestThrottle,
    OTPVerifyThrottle,
    PublicWriteThrottle,
    RegisterThrottle,
)
from common.utils import format_phone_display, mask_phone

logger = logging.getLogger("kemta.auth")
UserModel = get_user_model()


def _client_context(request) -> dict:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    ip = (forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR")) or None
    return {"ip": ip, "user_agent": request.META.get("HTTP_USER_AGENT", "")[:255]}


def _log_auth(request, *, event: str, phone: str = "", user=None, success: bool = True, detail: str = "") -> None:
    context = _client_context(request)
    AuthAuditLog.objects.create(
        phone=phone, user=user, event=event, success=success,
        ip_address=context["ip"], user_agent=context["user_agent"], detail=detail[:255],
    )


class OTPRequestView(APIView):
    """Étape 1 : envoi d'un code de vérification par SMS."""

    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes = [OTPRequestThrottle]

    def post(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if data.get("silent"):
            # Numéro inconnu sur un parcours « mot de passe oublié » : réponse
            # identique pour ne pas révéler l'existence du compte.
            return Response(
                {
                    "message": "Si un compte KEMTA est associé à ce numéro, un code vient de vous être envoyé.",
                    "expires_in": settings.OTP_TTL_SECONDS,
                    "resend_in": settings.OTP_RESEND_COOLDOWN_SECONDS,
                }
            )

        user = UserModel.objects.filter(phone=data["phone"]).first()
        otp = otp_service.issue_otp(
            phone=data["phone"], purpose=data["purpose"], request=request, user=user
        )
        payload = {
            "message": "Un code de vérification vous a été envoyé par SMS.",
            "phone_display": format_phone_display(otp.phone),
            "expires_in": otp.seconds_remaining,
            "resend_in": settings.OTP_RESEND_COOLDOWN_SECONDS,
            "attempts_allowed": otp.max_attempts,
        }
        if otp_service.dev_echo_enabled():
            # Uniquement en développement (DEBUG + OTP_DEV_ECHO) : évite de
            # dépendre d'une passerelle SMS. Jamais exposé en production.
            payload["dev_mode"] = True
            payload["dev_code"] = otp_service.dev_echo_code(otp.phone, otp.purpose)
        return Response(payload)


class OTPVerifyView(APIView):
    """Étape 2 : validation du code, renvoi d'un ticket d'échange à usage unique."""

    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes = [OTPVerifyThrottle]

    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Connexion directe par OTP : on émet les jetons immédiatement.
        if data["purpose"] == OTPPurpose.LOGIN:
            return self._login_with_otp(request, data)

        user = UserModel.objects.filter(phone=data["phone"]).first()
        ticket = otp_service.confirm_otp(
            phone=data["phone"], purpose=data["purpose"], code=data["code"], request=request, user=user
        )
        return Response(
            {
                "verified": True,
                "verification_ticket": ticket,
                "ticket_expires_in": otp_service.TICKET_TTL,
                "phone_display": format_phone_display(data["phone"]),
                "message": "Numéro vérifié. Vous pouvez continuer.",
            }
        )

    def _login_with_otp(self, request, data):
        otp_service.confirm_otp(
            phone=data["phone"], purpose=OTPPurpose.LOGIN, code=data["code"], request=request
        )
        user = UserModel.objects.filter(phone=data["phone"]).first()
        if user is None or not user.is_active:
            _log_auth(request, event=AuthAuditLog.Event.LOGIN_FAILED, phone=data["phone"],
                      success=False, detail="compte absent ou inactif")
            raise BusinessRuleError(
                "La connexion n'a pas pu aboutir. Contactez le support KEMTA si le problème persiste."
            )
        UserModel.objects.filter(pk=user.pk).update(phone_verified=True)
        tokens = issue_tokens_for_user(user, request=request, device_label="Connexion par code SMS")
        _log_auth(request, event=AuthAuditLog.Event.LOGIN_SUCCESS, phone=user.phone, user=user,
                  detail="otp")
        return Response({**tokens, "user": UserSummarySerializer(user).data})


class RegisterView(APIView):
    """Étape 3 (option A) : création du compte après vérification du numéro."""

    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes = [RegisterThrottle, PublicWriteThrottle]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if not otp_service.consume_ticket(
            ticket=data["verification_ticket"], phone=data["phone"], purpose=OTPPurpose.REGISTER
        ):
            raise BusinessRuleError(
                "La vérification de votre numéro a expiré. Demandez un nouveau code puis réessayez."
            )

        if data.get("email_conflict"):
            # On informe sans bloquer : l'e-mail est secondaire dans KEMTA.
            logger.info("email_conflict_ignored", extra={"phone": mask_phone(data["phone"])})

        user = create_user_from_registration(data=data, request=request)
        tokens = issue_tokens_for_user(user, request=request, device_label="Inscription")
        logger.info("user_registered", extra={"user_id": user.pk, "role": user.role})
        return Response(
            {
                "message": "Votre compte KEMTA est créé. Bienvenue !",
                "email_notice": (
                    "Cette adresse e-mail étant déjà utilisée, elle n'a pas été associée à votre compte."
                    if data.get("email_conflict") else ""
                ),
                "user": UserProfileSerializer(user).data,
                **tokens,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """Connexion principale : téléphone + mot de passe."""

    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes = [LoginThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            phone = str(request.data.get("phone") or "")
            try:
                from common.utils import normalize_phone

                phone = normalize_phone(phone)
            except ValueError:
                phone = ""
            _log_auth(request, event=AuthAuditLog.Event.LOGIN_FAILED, phone=phone, success=False,
                      detail="identifiants invalides")
            raise BusinessRuleError(
                "Numéro ou mot de passe incorrect. Vérifiez votre saisie, ou connectez-vous "
                "avec un code SMS si vous ne vous souvenez plus de votre mot de passe."
            )
        user = serializer.validated_data["user"]
        tokens = issue_tokens_for_user(user, request=request)
        _log_auth(request, event=AuthAuditLog.Event.LOGIN_SUCCESS, phone=user.phone, user=user)
        return Response({**tokens, "user": UserProfileSerializer(user).data})


class LoginOTPRequestView(APIView):
    """Connexion secondaire (sans mot de passe) : demande du code."""

    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes = [OTPRequestThrottle]

    def post(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = UserModel.objects.filter(phone=data["phone"]).first()
        otp = otp_service.issue_otp(
            phone=data["phone"], purpose=OTPPurpose.LOGIN, request=request, user=user
        )
        response = {
            "message": "Un code de connexion vous a été envoyé par SMS.",
            "phone_display": format_phone_display(otp.phone),
            "expires_in": otp.seconds_remaining,
            "resend_in": settings.OTP_RESEND_COOLDOWN_SECONDS,
            "attempts_allowed": otp.max_attempts,
        }
        if otp_service.dev_echo_enabled():
            response["dev_mode"] = True
            response["dev_code"] = otp_service.dev_echo_code(otp.phone, otp.purpose)
        return Response(response)


class TokenRefreshView(APIView):
    """Renouvellement du jeton d'accès — les jetons sont rotatifs."""

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def post(self, request):
        from apps.accounts.serializers import KemtaTokenRefreshSerializer

        serializer = KemtaTokenRefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)


class LogoutView(APIView):
    """Déconnexion : blacklist du refresh token + révocation de la session."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
                DeviceSession.objects.filter(jti=str(token["jti"]), user=request.user).update(
                    revoked_at=timezone.now()
                )
            except TokenError:
                pass
        _log_auth(request, event=AuthAuditLog.Event.LOGOUT, phone=request.user.phone, user=request.user)
        return Response({"message": "Vous êtes déconnecté. À bientôt sur KEMTA."})


class PasswordResetRequestView(APIView):
    """/auth/password/reset/ — demande de code (réponse toujours neutre)."""

    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes = [OTPRequestThrottle]

    def post(self, request):
        serializer = OTPRequestSerializer(data={**request.data, "purpose": OTPPurpose.PASSWORD_RESET})
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data["phone"]
        user = UserModel.objects.filter(phone=phone).first()
        neutral = {
            "message": "Si un compte KEMTA est associé à ce numéro, un code vous a été envoyé par SMS.",
            "resend_in": settings.OTP_RESEND_COOLDOWN_SECONDS,
        }
        if user is None:
            _log_auth(request, event=AuthAuditLog.Event.PASSWORD_RESET_REQUESTED, phone=phone,
                      success=False, detail="numéro inconnu")
            return Response(neutral)
        otp = otp_service.issue_otp(
            phone=phone, purpose=OTPPurpose.PASSWORD_RESET, request=request, user=user
        )
        _log_auth(request, event=AuthAuditLog.Event.PASSWORD_RESET_REQUESTED, phone=phone, user=user)
        return Response({**neutral, "expires_in": otp.seconds_remaining})


class PasswordResetConfirmView(APIView):
    """/auth/password/reset/confirm/ — nouveau mot de passe après OTP."""

    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes = [OTPVerifyThrottle]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = UserModel.objects.filter(phone=data["phone"]).first()
        if user is None:
            raise BusinessRuleError(
                "La réinitialisation n'a pas pu aboutir. Demandez un nouveau code puis réessayez."
            )
        if not otp_service.consume_ticket(
            ticket=data["verification_ticket"], phone=data["phone"], purpose=OTPPurpose.PASSWORD_RESET
        ):
            raise BusinessRuleError(
                "Votre vérification a expiré pour des raisons de sécurité. "
                "Demandez un nouveau code puis réessayez."
            )
        with transaction.atomic():
            user.set_password(data["password"])
            user.save(update_fields=["password", "updated_at"])
            # Toutes les sessions existantes sont révoquées : un mot de passe
            # réinitialisé doit invalider les jetons en circulation.
            DeviceSession.objects.filter(user=user, revoked_at__isnull=True).update(
                revoked_at=timezone.now()
            )
        _log_auth(request, event=AuthAuditLog.Event.PASSWORD_RESET_DONE, phone=user.phone, user=user)
        tokens = issue_tokens_for_user(user, request=request, device_label="Après réinitialisation")
        return Response(
            {
                "message": "Votre mot de passe a été réinitialisé. Vous êtes connecté.",
                "user": UserSummarySerializer(user).data,
                **tokens,
            }
        )


class PasswordChangeView(APIView):
    """/auth/password/change/ — changement volontaire (utilisateur connecté)."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [PublicWriteThrottle]

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.set_password(serializer.validated_data["password"])
        user.save(update_fields=["password", "updated_at"])
        DeviceSession.objects.filter(user=user, revoked_at__isnull=True).update(revoked_at=timezone.now())
        _log_auth(request, event=AuthAuditLog.Event.PASSWORD_CHANGED, phone=user.phone, user=user)
        tokens = issue_tokens_for_user(user, request=request, device_label="Après changement de mot de passe")
        return Response(
            {"message": "Votre mot de passe a été modifié. Vos autres appareils ont été déconnectés.", **tokens}
        )


class MeView(APIView):
    """Profil de l'utilisateur connecté (lecture et mise à jour partielle)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(self._payload(request.user))

    def patch(self, request):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(self._payload(request.user))

    @staticmethod
    def _payload(user) -> dict:
        """Réponse agrégée : profil + permissions + résumé d'espaces.

        Évite au frontend d'enchaîner trois appels au premier rendu.
        """
        permissions = sorted(get_user_permissions(user))
        return {
            "user": UserProfileSerializer(user).data,
            "permissions": permissions,
            "phone_verified": user.phone_verified,
            "spaces": _available_spaces(user),
        }


def _available_spaces(user) -> list[dict]:
    spaces = [{"key": "customer", "label": "Espace client", "available": True}]
    has_company = user.company_memberships.exists()
    spaces.append(
        {"key": "company", "label": "Espace entreprise BTP", "available": has_company or user.role == Role.COMPANY}
    )
    if user.is_kemta_team:
        spaces.append(
            {"key": "admin", "label": "Back-office KEMTA", "available": True}
        )
    return spaces


class MyPermissionsView(APIView):
    """Permissions effectives : le frontend masque, le backend vérifie."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            {
                "role": request.user.role,
                "role_label": request.user.get_role_display(),
                "is_kemta_team": request.user.is_kemta_team,
                "permissions": sorted(get_user_permissions(request.user)),
            }
        )


class PhoneChangeRequestView(APIView):
    """/auth/phone/change/ — envoi d'un code au nouveau numéro."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [OTPRequestThrottle]

    def post(self, request):
        serializer = PhoneChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_phone = serializer.validated_data["new_phone"]
        otp = otp_service.issue_otp(
            phone=new_phone, purpose=OTPPurpose.PHONE_CHANGE, request=request, user=request.user
        )
        return Response(
            {
                "message": "Un code de confirmation a été envoyé au nouveau numéro.",
                "phone_display": format_phone_display(new_phone),
                "expires_in": otp.seconds_remaining,
            }
        )


class PhoneChangeConfirmView(APIView):
    """/auth/phone/change/confirm/ — bascule effective du numéro."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [OTPVerifyThrottle]

    def post(self, request):
        serializer = PhoneChangeConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_phone = serializer.validated_data["new_phone"]

        if UserModel.objects.filter(phone=new_phone).exclude(pk=request.user.pk).exists():
            raise BusinessRuleError("Ce numéro vient d'être utilisé par un autre compte KEMTA.")
        ticket = otp_service.confirm_otp(
            phone=new_phone, purpose=OTPPurpose.PHONE_CHANGE,
            code=serializer.validated_data["code"], request=request, user=request.user,
        )
        if not otp_service.consume_ticket(
            ticket=ticket, phone=new_phone, purpose=OTPPurpose.PHONE_CHANGE
        ):  # pragma: no cover - vient d'être émis
            raise BusinessRuleError("La vérification du nouveau numéro a échoué. Réessayez.")

        old_phone = request.user.phone
        with transaction.atomic():
            request.user.phone = new_phone
            request.user.phone_verified = True
            request.user.save(update_fields=["phone", "phone_verified", "updated_at"])
        _log_auth(request, event=AuthAuditLog.Event.PHONE_CHANGED, phone=new_phone, user=request.user,
                  detail=f"ancien={mask_phone(old_phone)}")
        return Response(
            {
                "message": "Votre numéro de téléphone a été mis à jour.",
                "user": UserProfileSerializer(request.user).data,
            }
        )


class MySessionsView(ListAPIView):
    """Appareils connectés : l'utilisateur peut révoquer un accès suspect."""

    permission_classes = [IsAuthenticated]
    serializer_class = DeviceSessionSerializer
    pagination_class = None

    def get_queryset(self):
        return DeviceSession.objects.filter(user=self.request.user, revoked_at__isnull=True).order_by("-last_used_at")[:50]


class RevokeSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk: int):
        updated = DeviceSession.objects.filter(pk=pk, user=request.user).update(revoked_at=timezone.now())
        if not updated:
            raise BusinessRuleError("Cette session est introuvable ou déjà révoquée.")
        return Response({"message": "Cet appareil a été déconnecté."})


class MyAuthLogsView(ListAPIView):
    """Historique de sécurité de l'utilisateur (transparence)."""

    permission_classes = [IsAuthenticated]
    serializer_class = AuthAuditLogSerializer

    def get_queryset(self):
        return AuthAuditLog.objects.filter(user=self.request.user).order_by("-created_at")
