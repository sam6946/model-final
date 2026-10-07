"""Middlewares transverses : identifiant de trace et contexte de requête."""
from __future__ import annotations

import logging
import time
import uuid

from django.utils import translation

logger = logging.getLogger("kemta.request")

# En-têtes qu'on accepte de journaliser (jamais d'Authorization ni de cookie).
SAFE_HEADERS = ("user-agent", "x-forwarded-for", "x-real-ip", "referer")


class RequestContextMiddleware:
    """Ajoute un ``trace_id`` corrélable logs ↔ réponse HTTP ↔ frontend.

    Le trace_id est renvoyé dans l'en-tête ``X-Trace-Id`` pour que le support
    KEMTA puisse retrouver la requête exacte depuis un message client.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.trace_id = request.headers.get("X-Trace-Id") or uuid.uuid4().hex[:12]
        started = time.perf_counter()
        try:
            response = self.get_response(request)
        except Exception:
            logger.exception(
                "request_failed",
                extra={
                    "trace_id": request.trace_id,
                    "method": request.method,
                    "path": request.path,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                },
            )
            raise
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        response["X-Trace-Id"] = request.trace_id
        # Les requêtes lentes sont signalées pour analyse (objectif : API < 300 ms).
        if request.path.startswith("/api/") and duration_ms > 800:
            logger.warning(
                "slow_request",
                extra={
                    "trace_id": request.trace_id,
                    "method": request.method,
                    "path": request.path,
                    "duration_ms": duration_ms,
                    "status": response.status_code,
                },
            )
        return response


class FrenchLocaleMiddleware:
    """Impose le français, quelle que soit la langue du navigateur.

    KEMTA est un produit francophone destiné au Cameroun : ses messages d'erreur
    sont affichés tels quels dans l'interface. Or ``LocaleMiddleware`` active la
    langue annoncée par l'en-tête ``Accept-Language`` ; un navigateur configuré
    en anglais recevait donc « Authentication credentials were not provided. »
    au lieu de la phrase française équivalente.

    Placer ce middleware juste après ``LocaleMiddleware`` garantit que la langue
    choisie par le navigateur ne peut plus influencer le contenu des réponses :
    le message affiché à un utilisateur camerounais est toujours en français.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        with translation.override("fr"):
            request.LANGUAGE_CODE = "fr"
            response = self.get_response(request)
            response["Content-Language"] = "fr"
            return response
