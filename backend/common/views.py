"""Vues transverses : sondes de santé, dépôt de fichiers, contenus publics."""
from __future__ import annotations

import time

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.constants import AssetKind, AssetStatus, UploadKind
from common.models import Asset, FAQItem, Location, Testimonial, TrustStat
from common.pagination import KemtaPageNumberPagination
from common.serializers import (
    AssetSerializer,
    FAQItemSerializer,
    LocationSerializer,
    PresignRequestSerializer,
    TestimonialSerializer,
    TrustStatSerializer,
)
from common.services import uploads
from common.storage import object_storage
from common.throttling import PublicWriteThrottle


def health(_request) -> JsonResponse:
    """Liveness : le process répond-il ? (utilisé par Docker/K8s)."""
    return JsonResponse(
        {
            "status": "ok",
            "service": "kemta-api",
            "version": "1.0.0",
            "time": timezone.now().isoformat(),
        }
    )


def readiness(_request) -> JsonResponse:
    """Readiness : les dépendances critiques (DB, cache, stockage) répondent-elles ?"""
    checks: dict[str, dict] = {}
    healthy = True

    started = time.perf_counter()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        checks["database"] = {"status": "ok", "latency_ms": round((time.perf_counter() - started) * 1000, 2)}
    except Exception as exc:  # pragma: no cover
        healthy = False
        checks["database"] = {"status": "error", "detail": str(exc)[:200]}

    started = time.perf_counter()
    try:
        cache.set("kemta:health:ping", 1, 10)
        assert cache.get("kemta:health:ping") == 1
        checks["cache"] = {"status": "ok", "latency_ms": round((time.perf_counter() - started) * 1000, 2)}
    except Exception as exc:  # pragma: no cover
        healthy = False
        checks["cache"] = {"status": "error", "detail": str(exc)[:200]}

    checks["storage"] = {"status": "ok", "driver": object_storage.name}
    checks["celery_broker"] = {
        "status": "ok" if settings.CELERY_BROKER_URL else "disabled",
        "eager": settings.CELERY_TASK_ALWAYS_EAGER,
    }

    payload = {
        "status": "ready" if healthy else "degraded",
        "checks": checks,
        "time": timezone.now().isoformat(),
    }
    return JsonResponse(payload, status=200 if healthy else 503)


def spa_fallback(request, path: str = ""):
    """Sert l'application React (toutes les routes front sont côté client)."""
    index_path = settings.BASE_DIR / "frontend_dist" / "index.html"
    if index_path.exists():
        response = HttpResponse(index_path.read_text(encoding="utf-8"), content_type="text/html")
        response["Cache-Control"] = "no-cache"
        return response
    return render(request, "common/api_only.html", status=200)


class PresignUploadView(APIView):
    """Prépare un envoi direct vers l'object storage (pas de binaire via Django)."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [PublicWriteThrottle]
    throttle_scope_disabled = False

    def post(self, request):
        serializer = PresignRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        validated, presigned = uploads.presign(
            upload_kind=data["upload_kind"],
            filename=data["filename"],
            content_type=data.get("content_type") or "",
            size=data["size"],
            owner_id=request.user.pk,
        )
        asset = Asset.objects.create(
            kind=validated.kind,
            status=AssetStatus.PENDING,
            bucket=settings.OBJECT_STORAGE_BUCKET or "local",
            key=presigned.key,
            original_filename=validated.filename,
            mime_type=validated.content_type,
            size_bytes=validated.size,
            uploaded_by=request.user,
            is_public=data["upload_kind"] in {
                UploadKind.COMPANY_LOGO, UploadKind.COMPANY_COVER, UploadKind.REALIZATION_PHOTO,
                UploadKind.PROJECT_COVER, UploadKind.USER_AVATAR,
            },
        )
        return Response(
            {
                "asset_id": asset.id,
                "upload_url": presigned.upload_url,
                "method": presigned.method,
                "key": presigned.key,
                "fields": presigned.fields,
                "headers": presigned.headers,
                "expires_in": presigned.expires_in,
            },
            status=status.HTTP_201_CREATED,
        )


class DirectUploadView(APIView):
    """Repli serveur : reçoit le fichier, le range, puis planifie les variantes."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [PublicWriteThrottle]

    def post(self, request):
        fileobj = request.FILES.get("file")
        if fileobj is None:
            return Response(
                {"error": {"code": "missing_file", "message": "Aucun fichier reçu. Réessayez l'envoi."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        upload_kind = request.data.get("upload_kind") or UploadKind.EVIDENCE_PHOTO
        validated, key, checksum, buffer = uploads.store_direct(
            upload_kind=upload_kind,
            filename=fileobj.name,
            content_type=fileobj.content_type or "",
            fileobj=fileobj,
            owner_id=request.user.pk,
        )
        asset = Asset.objects.create(
            kind=validated.kind,
            status=AssetStatus.READY if validated.kind != AssetKind.IMAGE else AssetStatus.PENDING,
            bucket=settings.OBJECT_STORAGE_BUCKET or "local",
            key=key,
            original_filename=validated.filename,
            mime_type=validated.content_type,
            size_bytes=validated.size,
            checksum=checksum,
            uploaded_by=request.user,
            is_public=upload_kind in {
                UploadKind.COMPANY_LOGO, UploadKind.COMPANY_COVER, UploadKind.REALIZATION_PHOTO,
                UploadKind.PROJECT_COVER, UploadKind.USER_AVATAR,
            },
        )
        if validated.kind == AssetKind.IMAGE:
            from common.tasks import generate_image_variants

            generate_image_variants.delay(asset.pk)
        elif validated.kind == AssetKind.VIDEO:
            asset.variants = {"original": key}
            asset.status = AssetStatus.READY
            asset.save(update_fields=["variants", "status", "updated_at"])

        return Response(AssetSerializer(asset).data, status=status.HTTP_201_CREATED)


class AssetDetailView(APIView):
    """Consultation d'un fichier : seuls le propriétaire et l'équipe KEMTA y accèdent."""

    permission_classes = [IsAuthenticated]

    def get(self, _request, pk: int):
        try:
            asset = Asset.objects.get(pk=pk)
        except Asset.DoesNotExist:
            return Response(
                {"error": {"code": "not_found", "message": "Ce fichier n'existe pas ou a été supprimé."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        if not (asset.is_public or asset.uploaded_by_id == _request.user.pk or _request.user.is_kemta_team):
            return Response(
                {"error": {"code": "forbidden", "message": "Vous n'avez pas accès à ce fichier."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(AssetSerializer(asset).data)


class AssetCompleteView(APIView):
    """Confirme qu'un envoi direct S3 est terminé, pour lancer le traitement."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk: int):
        try:
            asset = Asset.objects.get(pk=pk, uploaded_by=request.user)
        except Asset.DoesNotExist:
            return Response(
                {"error": {"code": "not_found", "message": "Ce fichier est introuvable."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        if not object_storage.exists(asset.key):
            asset.status = AssetStatus.FAILED
            asset.save(update_fields=["status", "updated_at"])
            return Response(
                {
                    "error": {
                        "code": "upload_missing",
                        "message": "L'envoi n'a pas abouti. Vérifiez votre connexion puis réessayez.",
                    }
                },
                status=status.HTTP_409_CONFLICT,
            )
        if asset.kind == AssetKind.IMAGE:
            from common.tasks import generate_image_variants

            generate_image_variants.delay(asset.pk)
        else:
            asset.variants = {"original": asset.key}
            asset.status = AssetStatus.READY
            asset.save(update_fields=["variants", "status", "updated_at"])
        return Response(AssetSerializer(asset).data)


class LocationListView(APIView):
    """Référentiel de localisations (mis en cache : change très rarement)."""

    permission_classes = [AllowAny]

    def get(self, request):
        from common.catalog import locations_payload

        country = request.query_params.get("country")
        kind = request.query_params.get("kind")
        return Response(locations_payload(country=country, kind=kind))


class PublicContentAPIView(APIView):
    """Contenus publics éditoriaux : FAQ, témoignages, chiffres de confiance."""

    permission_classes = [AllowAny]

    def get(self, _request):
        from common.catalog import public_content

        return Response(public_content())
