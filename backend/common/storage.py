"""Abstraction de stockage objet (S3 / Cloudflare R2 / MinIO) + repli local.

Aucun binaire n'est stocké en base : la DB ne contient que des métadonnées et
des clés d'objet. En développement (ou sans credentials), un pilote local
écrit dans MEDIA_ROOT afin que l'application reste utilisable hors production.
"""
from __future__ import annotations

import logging
import mimetypes
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from django.conf import settings
from django.utils import timezone
from django.utils.text import get_valid_filename

logger = logging.getLogger("kemta.storage")


@dataclass(frozen=True)
class PresignedUpload:
    """Informations renvoyées au frontend pour un envoi direct."""

    upload_url: str
    method: str
    key: str
    fields: dict[str, str]
    headers: dict[str, str]
    expires_in: int


class BaseObjectStorage:
    name = "base"

    def put(self, key: str, fileobj: BinaryIO, content_type: str = "", *, public: bool = False) -> None:
        raise NotImplementedError

    def open(self, key: str) -> BinaryIO:
        raise NotImplementedError

    def delete(self, key: str) -> None:
        raise NotImplementedError

    def exists(self, key: str) -> bool:
        raise NotImplementedError

    def url(self, key: str, *, public: bool = False) -> str:
        raise NotImplementedError

    def presigned_put(self, key: str, content_type: str, *, public: bool = False) -> PresignedUpload:
        raise NotImplementedError

    def size(self, key: str) -> int:
        try:
            return os.path.getsize(self.path(key)) if hasattr(self, "path") else 0
        except OSError:
            return 0


class LocalObjectStorage(BaseObjectStorage):
    """Pilote de développement : écrit dans MEDIA_ROOT (servi par Django/Nginx)."""

    name = "local"

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, key: str) -> str:
        return str(self.root / key)

    def put(self, key: str, fileobj: BinaryIO, content_type: str = "", *, public: bool = False) -> None:
        target = self.root / key
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "wb") as handle:
            for chunk in iter(lambda: fileobj.read(1024 * 256), b""):
                handle.write(chunk)

    def open(self, key: str) -> BinaryIO:
        return open(self.root / key, "rb")

    def delete(self, key: str) -> None:
        try:
            os.remove(self.root / key)
        except OSError:
            logger.warning("storage_delete_missing", extra={"key": key})

    def exists(self, key: str) -> bool:
        return (self.root / key).exists()

    def url(self, key: str, *, public: bool = False) -> str:
        if not key:
            return ""
        if key.startswith("http://") or key.startswith("https://"):
            return key
        base = settings.MEDIA_URL.rstrip("/")
        return f"{base}/{key.lstrip('/')}"

    def presigned_put(self, key: str, content_type: str, *, public: bool = False) -> PresignedUpload:
        # En local, pas de S3 : le frontend envoie le fichier à l'API
        # (endpoint ``/uploads/direct/``) qui le transmet au pilote actif.
        return PresignedUpload(
            upload_url="/api/v1/uploads/direct/",
            method="POST",
            key=key,
            fields={"key": key, "content_type": content_type},
            headers={},
            expires_in=settings.OBJECT_STORAGE_PRESIGN_TTL,
        )

    def copy(self, source_key: str, target_key: str) -> None:
        target = self.root / target_key
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(self.root / source_key, target)


class S3ObjectStorage(BaseObjectStorage):
    """Pilote S3 compatible (AWS S3, Cloudflare R2, MinIO, Wasabi)."""

    name = "s3"

    def __init__(self) -> None:
        import boto3  # import paresseux : boto3 n'est requis qu'en production

        self.bucket = settings.OBJECT_STORAGE_BUCKET
        session_kwargs: dict = {
            "aws_access_key_id": settings.OBJECT_STORAGE_ACCESS_KEY,
            "aws_secret_access_key": settings.OBJECT_STORAGE_SECRET_KEY,
            "region_name": settings.OBJECT_STORAGE_REGION,
        }
        if settings.OBJECT_STORAGE_ENDPOINT:
            session_kwargs["endpoint_url"] = settings.OBJECT_STORAGE_ENDPOINT
        self.client = boto3.client("s3", **session_kwargs)
        self.public_base = (settings.OBJECT_STORAGE_PUBLIC_BASE_URL or "").rstrip("/")
        self._cache_ok: dict[str, bool] = {}

    def put(self, key: str, fileobj: BinaryIO, content_type: str = "", *, public: bool = False) -> None:
        extra = {"ContentType": content_type} if content_type else {}
        if public:
            extra["ACL"] = "public-read"
        self.client.upload_fileobj(fileobj, self.bucket, key, ExtraArgs=extra or None)

    def open(self, key: str) -> BinaryIO:
        return self.client.get_object(Bucket=self.bucket, Key=key)["Body"]

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)

    def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False

    def url(self, key: str, *, public: bool = False) -> str:
        """URL publique si possible, sinon URL signée à durée limitée."""
        if not key:
            return ""
        if key.startswith("http"):
            return key
        if public and self.public_base:
            return f"{self.public_base}/{key}"
        try:
            return self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=settings.OBJECT_STORAGE_PRESIGN_TTL,
            )
        except Exception:  # pragma: no cover
            logger.warning("presign_get_failed", extra={"key": key})
            return f"{self.public_base}/{key}" if self.public_base else ""

    def presigned_put(self, key: str, content_type: str, *, public: bool = False) -> PresignedUpload:
        params = {"Bucket": self.bucket, "Key": key, "ContentType": content_type or "application/octet-stream"}
        if public:
            params["ACL"] = "public-read"
        url = self.client.generate_presigned_url(
            "put_object", Params=params, ExpiresIn=settings.OBJECT_STORAGE_PRESIGN_TTL
        )
        return PresignedUpload(
            upload_url=url,
            method="PUT",
            key=key,
            fields={},
            headers={"Content-Type": content_type or "application/octet-stream"},
            expires_in=settings.OBJECT_STORAGE_PRESIGN_TTL,
        )


def build_storage() -> BaseObjectStorage:
    if settings.OBJECT_STORAGE_BUCKET and settings.OBJECT_STORAGE_ACCESS_KEY:
        try:
            return S3ObjectStorage()
        except Exception:  # pragma: no cover - configuration incomplète
            logger.exception("s3_storage_init_failed_fallback_local")
    return LocalObjectStorage(settings.MEDIA_ROOT)


object_storage: BaseObjectStorage = build_storage()


def build_object_key(*, kind: str, filename: str, owner_id: int | None = None, prefix: str = "media") -> str:
    """Clé d'objet lisible et cloisonnée :

    ``media/2026/10/evidence/42/1696531200-photo-chantier.jpg``
    Les préfixes par type/année facilitent la gestion du cycle de vie S3
    (règles de transition vers Glacier, purge des brouillons, etc.).
    """
    today = timezone.localdate()
    safe = get_valid_filename(filename or "fichier")[:120]
    owner = f"{owner_id}/" if owner_id else ""
    stamp = int(timezone.now().timestamp())
    return f"{prefix}/{today:%Y/%m}/{kind.lower()}/{owner}{stamp}-{safe}"


def guess_content_type(filename: str) -> str:
    return mimetypes.guess_type(filename)[0] or "application/octet-stream"
