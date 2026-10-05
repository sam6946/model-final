"""Backoffice Django : supervision rapide des données transverses."""
from django.contrib import admin

from common.models import (
    Asset,
    Configuration,
    FAQItem,
    IdempotencyKey,
    Location,
    ReferenceCounter,
    Testimonial,
    TrustStat,
)


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "region", "country", "is_active")
    list_filter = ("kind", "country", "is_active")
    search_fields = ("name", "region", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ("original_filename", "kind", "status", "size_bytes", "uploaded_by", "created_at")
    list_filter = ("kind", "status", "is_public")
    search_fields = ("original_filename", "key")
    readonly_fields = ("checksum", "variants", "created_at", "updated_at")
    date_hierarchy = "created_at"


@admin.register(Configuration)
class ConfigurationAdmin(admin.ModelAdmin):
    list_display = ("key", "label", "is_public", "updated_at")
    search_fields = ("key", "label")


@admin.register(FAQItem)
class FAQItemAdmin(admin.ModelAdmin):
    list_display = ("question", "category", "order", "is_active")
    list_filter = ("category", "is_active")
    list_editable = ("order", "is_active")
    search_fields = ("question", "answer")


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ("author_name", "author_city", "author_country", "rating", "is_published")
    list_filter = ("is_published", "author_country", "rating")
    list_editable = ("is_published",)
    search_fields = ("author_name", "quote")


@admin.register(TrustStat)
class TrustStatAdmin(admin.ModelAdmin):
    list_display = ("label", "value", "order", "is_active")
    list_editable = ("order", "is_active")


@admin.register(ReferenceCounter)
class ReferenceCounterAdmin(admin.ModelAdmin):
    list_display = ("prefix", "year", "last_number", "updated_at")
    readonly_fields = ("updated_at",)


@admin.register(IdempotencyKey)
class IdempotencyKeyAdmin(admin.ModelAdmin):
    list_display = ("key", "scope", "user", "response_status", "created_at")
    list_filter = ("scope",)
    search_fields = ("key",)
