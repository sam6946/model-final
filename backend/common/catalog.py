"""Agrégation des contenus publics, mise en cache Redis (TTL explicites).

C'est ce qui permet à la landing page de tenir la charge : une requête
agrégée et servie depuis le cache au lieu de 6 appels séparés.
"""
from __future__ import annotations

from django.core.cache import cache

from common.cache import TTL, make_key
from common.models import FAQItem, Location, Testimonial, TrustStat
from common.serializers import FAQItemSerializer, LocationSerializer, TestimonialSerializer, TrustStatSerializer


def locations_payload(*, country: str | None = None, kind: str | None = None) -> dict:
    key = make_key("locations", country, kind)
    cached = cache.get(key)
    if cached is not None:
        return cached
    queryset = Location.objects.filter(is_active=True)
    if country:
        queryset = queryset.filter(country=country)
    if kind:
        queryset = queryset.filter(kind=kind)
    items = list(queryset.only("id", "name", "slug", "region", "country", "kind", "latitude", "longitude"))
    payload = {
        "count": len(items),
        "cities": LocationSerializer([i for i in items if i.kind in ("CITY", "DIASPORA_CITY")], many=True).data,
        "regions": LocationSerializer([i for i in items if i.kind == "REGION"], many=True).data,
    }
    cache.set(key, payload, TTL["locations"])
    return payload


def public_content() -> dict:
    """FAQ + témoignages + chiffres : un seul appel pour toute la landing."""
    key = make_key("public_content", "v1")
    cached = cache.get(key)
    if cached is not None:
        return cached

    faqs = list(FAQItem.objects.filter(is_active=True).only("id", "category", "question", "answer", "order"))
    testimonials = list(
        Testimonial.objects.filter(is_published=True)
        .select_related("photo", "project")
        .only(
            "id", "author_name", "author_role", "author_city", "author_country", "quote",
            "rating", "photo__key", "photo__variants", "photo__is_public", "photo__kind",
            "project__name",
        )[:12]
    )
    stats = list(TrustStat.objects.filter(is_active=True).only("id", "label", "value", "hint", "icon", "order"))

    grouped: dict[str, list] = {}
    for item in FAQItemSerializer(faqs, many=True).data:
        grouped.setdefault(item["category"], []).append(item)

    payload = {
        "faq": grouped,
        "testimonials": TestimonialSerializer(testimonials, many=True).data,
        "trust_stats": TrustStatSerializer(stats, many=True).data,
    }
    cache.set(key, payload, TTL["faq"])
    return payload
