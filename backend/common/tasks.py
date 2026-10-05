"""Tâches Celery transverses (traitement d'images, maintenance du cache)."""
from __future__ import annotations

import logging

from celery import shared_task
from django.core.cache import cache

from common.cache import bump_version
from common.constants import AssetStatus
from common.models import Asset

logger = logging.getLogger("kemta.tasks")


@shared_task(name="common.generate_image_variants", bind=True, max_retries=3, default_retry_delay=20)
def generate_image_variants(self, asset_id: int) -> dict:
    """Compresse et décline une photo (thumbnail / medium / large, WebP).

    Une photo de chantier peut peser 8 Mo : le client ne doit jamais la
    télécharger. On produit donc des variantes légères côté serveur.
    """
    from common.services.uploads import process_image_variants

    try:
        asset = Asset.objects.get(pk=asset_id)
    except Asset.DoesNotExist:
        logger.warning("asset_missing", extra={"asset_id": asset_id})
        return {"status": "missing"}

    if asset.kind != "IMAGE":
        return {"status": "skipped"}

    result = process_image_variants(key=asset.key, mime_type=asset.mime_type)
    if not result["variants"]:
        asset.status = AssetStatus.FAILED
        asset.save(update_fields=["status", "updated_at"])
        return {"status": "failed"}

    asset.variants = result["variants"]
    asset.width = result["width"]
    asset.height = result["height"]
    asset.status = AssetStatus.READY
    asset.save(update_fields=["variants", "width", "height", "status", "updated_at"])
    return {"status": "ready", "variants": sorted(result["variants"].keys())}


@shared_task(name="common.purge_failed_uploads")
def purge_failed_uploads(days: int = 7) -> int:
    """Supprime les dépôts en échec/abandonnés et leurs objets orphelins."""
    from datetime import timedelta

    from django.utils import timezone

    from common.storage import object_storage

    cutoff = timezone.now() - timedelta(days=days)
    pending = Asset.objects.filter(status__in=[AssetStatus.PENDING, AssetStatus.FAILED], created_at__lt=cutoff)
    removed = 0
    for asset in pending.iterator(chunk_size=200):
        try:
            object_storage.delete(asset.key)
        except Exception:  # pragma: no cover
            logger.warning("orphan_delete_failed", extra={"key": asset.key})
        asset.delete()
        removed += 1
    return removed


@shared_task(name="common.refresh_public_caches")
def refresh_public_caches() -> dict:
    """Préchauffe les caches publics (landing) après déploiement."""
    from common.catalog import locations_payload, public_content

    cache.delete_many(
        [
            "kemta:cache:public_content",
        ]
    )
    bump_version("public_content")
    public_content()
    locations_payload()
    return {"status": "refreshed"}
