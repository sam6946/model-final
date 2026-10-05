"""Helpers de cache Redis : clés versionnées, invalidation par préfixe."""
from __future__ import annotations

import functools
import hashlib
import logging
from typing import Any, Callable

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger("kemta.cache")

# TTL (secondes) par nature de donnée — définis, jamais « aveugles ».
TTL = {
    "permissions": 60 * 10,
    "configuration": 60 * 30,
    "service_catalog": 60 * 30,
    "faq": 60 * 60,
    "testimonials": 60 * 30,
    "company_public": 60 * 5,
    "catalog_listing": 60 * 3,
    "locations": 60 * 60 * 6,
    "plans": 60 * 15,
    "dashboard_stats": 60 * 2,
    "opportunities": 60 * 2,
    "short": 30,
}


def make_key(ns: str, *parts: Any) -> str:
    raw = ":".join(str(part) for part in parts if part not in (None, ""))
    digest = hashlib.blake2b(raw.encode("utf-8"), digest_size=8).hexdigest()
    return f"kemta:{ns}:{digest}"


def cached(namespace: str, *, ttl_key: str | None = None, timeout: int | None = None,
           skip_if: Callable[..., bool] | None = None):
    """Décorateur : met le résultat en cache Redis avec un TTL explicite.

    ``skip_if`` permet de ne pas mettre en cache selon les arguments
    (ex. ne jamais cacher la page 3 d'une liste filtrée par un utilisateur).
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if skip_if is not None and skip_if(*args, **kwargs):
                return func(*args, **kwargs)
            key = make_key(namespace, *args[1:], *sorted((k, v) for k, v in kwargs.items()))
            sentinel = object()
            hit = cache.get(key, sentinel)
            if hit is not sentinel:
                return hit
            value = func(*args, **kwargs)
            timeout_value = timeout if timeout is not None else TTL.get(ttl_key or namespace, 300)
            cache.set(key, value, timeout_value)
            return value

        wrapper.cache_clear = lambda *a, **k: cache.delete(  # type: ignore[attr-defined]
            make_key(namespace, *a, *sorted(k.items()))
        )
        return wrapper

    return decorator


def invalidate(namespace: str, *parts: Any) -> None:
    """Invalide une entrée précise après écriture (jamais tout le cache)."""
    try:
        cache.delete(make_key(namespace, *parts))
    except Exception:  # pragma: no cover - le cache ne doit jamais casser une requête
        logger.warning("cache_invalidate_failed", extra={"namespace": namespace})


def invalidate_many(namespace: str, keys: list[tuple]) -> None:
    for parts in keys:
        invalidate(namespace, *parts)


def bump_version(namespace: str) -> int:
    """Incrémente une version de namespace pour invalider en masse sans scan."""
    key = f"kemta:version:{namespace}"
    try:
        return cache.incr(key)
    except ValueError:
        cache.set(key, 1, None)
        return 1


def get_version(namespace: str) -> int:
    return cache.get(f"kemta:version:{namespace}", 0)


def using_redis() -> bool:
    return bool(getattr(settings, "REDIS_URL", ""))
