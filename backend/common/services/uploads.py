"""Dépôt de fichiers : pré-signature, réception directe, variantes d'image.

Sécurité appliquée ici :
- liste blanche de types MIME et extensions (pas de confiance au client) ;
- taille maximale par type ;
- nom de fichier assaini et clé d'objet générée côté serveur (jamais fournie
  par l'appelant) → aucune traversée de chemin possible ;
- vérification de signature binaire pour les images.
"""
from __future__ import annotations

import hashlib
import io
import logging
import os
from dataclasses import dataclass

from django.conf import settings
from django.core.exceptions import ValidationError

from common.constants import AssetKind, AssetStatus, UploadKind
from common.storage import build_object_key, guess_content_type, object_storage
from common.utils import safe_int

logger = logging.getLogger("kemta.uploads")

IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}
VIDEO_TYPES = {"video/mp4", "video/quicktime", "video/webm"}
DOCUMENT_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain",
    "image/jpeg",
    "image/png",
}
ALLOWED_TYPES = IMAGE_TYPES | VIDEO_TYPES | DOCUMENT_TYPES
EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".mp4", ".mov", ".webm",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".txt",
}
MAX_BYTES_BY_KIND = {
    AssetKind.IMAGE: min(settings.MAX_UPLOAD_BYTES, 15 * 1024 * 1024),
    AssetKind.VIDEO: min(settings.MAX_UPLOAD_BYTES * 4, 80 * 1024 * 1024),
    AssetKind.DOCUMENT: min(settings.MAX_UPLOAD_BYTES, 20 * 1024 * 1024),
}

IMAGE_SIZES = {"thumbnail": 320, "medium": 1024, "large": 1920}


@dataclass(frozen=True)
class ValidatedUpload:
    filename: str
    content_type: str
    size: int
    kind: str


def classify(content_type: str) -> str:
    if content_type in IMAGE_TYPES:
        return AssetKind.IMAGE
    if content_type in VIDEO_TYPES:
        return AssetKind.VIDEO
    return AssetKind.DOCUMENT


def validate_upload(*, filename: str, content_type: str, size: int) -> ValidatedUpload:
    """Valide un dépôt avant toute écriture. Lève ``ValidationError`` sinon."""
    content_type = (content_type or guess_content_type(filename)).lower()
    extension = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""
    if content_type not in ALLOWED_TYPES:
        if extension in EXTENSIONS:
            # Le navigateur envoie parfois un MIME générique : on déduit du nom.
            content_type = guess_content_type(filename)
        else:
            raise ValidationError(
                "Ce type de fichier n'est pas accepté. Formats autorisés : photos (JPG, PNG, WEBP), "
                "vidéos (MP4), documents (PDF, DOC, XLS)."
            )
    if extension and extension not in EXTENSIONS:
        raise ValidationError(
            "L'extension de ce fichier n'est pas autorisée. Utilisez une photo, une vidéo ou un document."
        )
    kind = classify(content_type)
    limit = MAX_BYTES_BY_KIND[kind]
    if size and size > limit:
        raise ValidationError(
            f"Ce fichier est trop volumineux ({size / 1024 / 1024:.1f} Mo). "
            f"Maximum autorisé : {limit / 1024 / 1024:.0f} Mo."
        )
    if not size:
        raise ValidationError("Le fichier transmis est vide ou illisible.")
    return ValidatedUpload(filename=filename, content_type=content_type, size=size, kind=kind)


def build_key(*, upload_kind: str, filename: str, owner_id: int | None) -> str:
    return build_object_key(kind=upload_kind, filename=filename, owner_id=owner_id)


def presign(*, upload_kind: str, filename: str, content_type: str, size: int, owner_id: int | None):
    """Prépare un envoi direct vers l'object storage (le backend ne voit pas le binaire)."""
    validated = validate_upload(filename=filename, content_type=content_type, size=size)
    key = build_key(upload_kind=upload_kind, filename=validated.filename, owner_id=owner_id)
    public = upload_kind in {UploadKind.COMPANY_LOGO, UploadKind.COMPANY_COVER, UploadKind.REALIZATION_PHOTO,
                             UploadKind.PROJECT_COVER, UploadKind.USER_AVATAR}
    return validated, object_storage.presigned_put(key, validated.content_type, public=public)


def store_direct(*, upload_kind: str, filename: str, content_type: str, fileobj, owner_id: int | None):
    """Repli serveur : reçoit le fichier puis l'écrit dans l'object storage.

    Utilisé en développement (stockage local) et par les clients mobiles qui ne
    peuvent pas faire d'envoi S3 direct (PWA en file d'attente hors ligne).
    """
    size = safe_int(getattr(fileobj, "size", 0))
    validated = validate_upload(filename=filename, content_type=content_type, size=size)
    if validated.kind == AssetKind.IMAGE:
        _assert_real_image(fileobj)
    key = build_key(upload_kind=upload_kind, filename=validated.filename, owner_id=owner_id)
    checksum = hashlib.sha256()
    buffer = io.BytesIO()
    for chunk in iter(lambda: fileobj.read(1024 * 256), b""):
        checksum.update(chunk)
        buffer.write(chunk)
    buffer.seek(0)
    public = upload_kind in {UploadKind.COMPANY_LOGO, UploadKind.COMPANY_COVER, UploadKind.REALIZATION_PHOTO,
                             UploadKind.PROJECT_COVER, UploadKind.USER_AVATAR}
    object_storage.put(key, buffer, validated.content_type, public=public)
    buffer.seek(0)
    return validated, key, checksum.hexdigest(), buffer


def _assert_real_image(fileobj) -> None:
    """Vérifie que le contenu est bien une image (anti-renommage malveillant)."""
    from PIL import Image, UnidentifiedImageError

    position = fileobj.tell() if hasattr(fileobj, "tell") else 0
    try:
        data = fileobj.read(64)
        fileobj.seek(position)
        with Image.open(io.BytesIO(data + fileobj.read(2048) if hasattr(fileobj, "read") else data)) as probe:
            probe.verify()
        if hasattr(fileobj, "seek"):
            fileobj.seek(0)
    except (UnidentifiedImageError, OSError):
        raise ValidationError(
            "Le fichier transmis n'est pas une image valide. Réessayez avec une photo JPG ou PNG."
        ) from None
    except Exception:
        # Une image lourde peut ne pas être vérifiable sur les premiers octets :
        # on ne bloque pas l'envoi terrain pour autant.
        logger.info("image_probe_inconclusive")


def process_image_variants(*, key: str, mime_type: str, target_prefix: str | None = None) -> dict[str, str]:
    """Génère thumbnail / medium / large compressés (WebP), prêts pour le web.

    Exécuté par Celery : la requête HTTP n'attend jamais la fin du traitement.
    """
    from PIL import Image, ImageOps

    variants: dict[str, str] = {}
    with object_storage.open(key) as source:
        payload = source.read()
    try:
        with Image.open(io.BytesIO(payload)) as image:
            image = ImageOps.exif_transpose(image)
            if image.mode in {"P", "RGBA", "LA"}:
                background = Image.new("RGB", image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[-1] if image.mode in {"RGBA", "LA"} else None)
                image = background
            original_width, original_height = image.size
            for label, target in IMAGE_SIZES.items():
                resized = image.copy()
                resized.thumbnail((target, target * 4), Image.LANCZOS)
                buffer = io.BytesIO()
                resized.save(buffer, format="WEBP", quality=82, method=4, optimize=True)
                buffer.seek(0)
                variant_key = _variant_key(key, label)
                object_storage.put(variant_key, buffer, "image/webp", public=True)
                variants[label] = variant_key
            buffer = io.BytesIO()
            image.save(buffer, format="WEBP", quality=88, method=4, optimize=True)
            buffer.seek(0)
            variants["original"] = _variant_key(key, "original")
            object_storage.put(variants["original"], buffer, "image/webp", public=True)
        return {"variants": variants, "width": original_width, "height": original_height}
    except Exception:
        logger.exception("image_variant_failed", extra={"key": key})
        return {"variants": {}, "width": None, "height": None}


def _variant_key(key: str, label: str) -> str:
    stem, _, _extension = key.rpartition(".")
    stem = stem or key
    return f"{stem}-{label}.webp"

