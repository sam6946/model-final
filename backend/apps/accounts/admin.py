"""Backoffice comptes : utilisateurs, permissions, sécurité."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.accounts.models import (
    AuthAuditLog,
    DeviceSession,
    OTPVerification,
    Permission,
    PhoneVerification,
    RolePermission,
    User,
)
from common.utils import mask_phone


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("phone", "full_name", "role", "phone_verified", "is_active", "created_at")
    list_filter = ("role", "phone_verified", "is_active", "is_staff", "country")
    search_fields = ("phone", "first_name", "last_name", "email")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    readonly_fields = ("created_at", "updated_at", "last_login", "last_seen_at", "terms_accepted_at")
    fieldsets = (
        ("Identité", {"fields": ("phone", "phone_verified", "first_name", "last_name", "avatar")}),
        ("Contact", {"fields": ("email", "country", "city", "preferred_locale", "marketing_opt_in")}),
        ("Rôle & accès", {"fields": ("role", "is_active", "is_staff", "is_superuser")}),
        ("Sécurité", {"fields": ("password", "last_login", "last_seen_at", "terms_accepted_at")}),
        ("Dates", {"fields": ("created_at", "updated_at")}),
    )
    add_fieldsets = (
        (
            "Nouvel utilisateur KEMTA",
            {
                "classes": ("wide",),
                "fields": ("phone", "first_name", "last_name", "role", "password1", "password2"),
            },
        ),
    )

    @admin.display(description="Nom complet", ordering="first_name")
    def full_name(self, obj: User) -> str:
        return obj.full_name


@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    list_display = ("phone_masked", "purpose", "status_label", "attempts", "created_at", "expires_at")
    list_filter = ("purpose", "created_at")
    search_fields = ("phone",)
    readonly_fields = ("code_hash", "salt", "created_at", "used_at", "invalidated_at")
    date_hierarchy = "created_at"

    def has_add_permission(self, request) -> bool:
        return False  # les codes se génèrent uniquement par le parcours applicatif

    @admin.display(description="Téléphone")
    def phone_masked(self, obj: OTPVerification) -> str:
        return mask_phone(obj.phone)

    @admin.display(description="État")
    def status_label(self, obj: OTPVerification) -> str:
        return obj.status_label


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ("code", "label", "category")
    list_filter = ("category",)
    search_fields = ("code", "label")


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = ("role", "permission", "allowed", "updated_at")
    list_filter = ("role", "allowed")
    search_fields = ("permission__code",)
    autocomplete_fields = ("permission",)


@admin.register(AuthAuditLog)
class AuthAuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "event", "phone_masked", "success", "ip_address")
    list_filter = ("event", "success", "created_at")
    search_fields = ("phone", "detail")
    date_hierarchy = "created_at"

    def has_add_permission(self, request) -> bool:
        return False

    @admin.display(description="Téléphone")
    def phone_masked(self, obj: AuthAuditLog) -> str:
        return mask_phone(obj.phone)


@admin.register(DeviceSession)
class DeviceSessionAdmin(admin.ModelAdmin):
    list_display = ("user", "device_label", "ip_address", "last_used_at", "expires_at", "revoked_at")
    list_filter = ("revoked_at",)
    search_fields = ("user__phone", "device_label")
    date_hierarchy = "last_used_at"


@admin.register(PhoneVerification)
class PhoneVerificationAdmin(admin.ModelAdmin):
    list_display = ("phone_masked", "purpose", "verified_at", "user")
    list_filter = ("purpose",)
    search_fields = ("phone",)

    @admin.display(description="Téléphone")
    def phone_masked(self, obj: PhoneVerification) -> str:
        return mask_phone(obj.phone)
