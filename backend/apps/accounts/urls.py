"""Routes d'authentification (`/api/v1/auth/...`)."""
from django.urls import path

from apps.accounts.views import (
    LoginOTPRequestView,
    LoginView,
    LogoutView,
    MeView,
    MyAuthLogsView,
    MyPermissionsView,
    MySessionsView,
    OTPRequestView,
    OTPVerifyView,
    PasswordChangeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    PhoneChangeConfirmView,
    PhoneChangeRequestView,
    RegisterView,
    RevokeSessionView,
    TokenRefreshView,
)

urlpatterns = [
    # Parcours OTP (téléphone d'abord)
    path("otp/request/", OTPRequestView.as_view(), name="auth-otp-request"),
    path("otp/verify/", OTPVerifyView.as_view(), name="auth-otp-verify"),
    # Inscription / connexion
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("login/otp/request/", LoginOTPRequestView.as_view(), name="auth-login-otp-request"),
    path("login/otp/verify/", OTPVerifyView.as_view(), name="auth-login-otp-verify"),
    path("token/refresh/", TokenRefreshView.as_view(), name="auth-token-refresh"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    # Mot de passe
    path("password/reset/", PasswordResetRequestView.as_view(), name="auth-password-reset"),
    path("password/reset/confirm/", PasswordResetConfirmView.as_view(), name="auth-password-reset-confirm"),
    path("password/change/", PasswordChangeView.as_view(), name="auth-password-change"),
    # Profil & sécurité
    path("me/", MeView.as_view(), name="auth-me"),
    path("permissions/", MyPermissionsView.as_view(), name="auth-permissions"),
    path("phone/change/", PhoneChangeRequestView.as_view(), name="auth-phone-change"),
    path("phone/change/confirm/", PhoneChangeConfirmView.as_view(), name="auth-phone-change-confirm"),
    path("sessions/", MySessionsView.as_view(), name="auth-sessions"),
    path("sessions/<int:pk>/revoke/", RevokeSessionView.as_view(), name="auth-session-revoke"),
    path("logs/", MyAuthLogsView.as_view(), name="auth-logs"),
]
