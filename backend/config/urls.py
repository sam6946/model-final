"""Routage racine KEMTA.

- /api/v1/... : API versionnée (v2 pourra être ajoutée sans casser v1)
- /admin/     : backoffice Django (supervision interne)
- /health/    : sondes d'exploitation (liveness / readiness)
- /           : SPA React servie par Nginx (ou la vue d'accueil de secours)
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from common.views import api_not_found, health, readiness, spa_fallback

api_v1 = [
    path("auth/", include("apps.accounts.urls")),
    path("", include("apps.dashboard.urls")),
    path("", include("apps.service_requests.urls")),
    path("", include("apps.projects.urls")),
    path("", include("apps.evidences.urls")),
    path("", include("apps.reports.urls")),
    path("", include("apps.customers.urls")),
    path("", include("apps.properties.urls")),
    path("", include("apps.maintenance.urls")),
    path("", include("apps.construction.urls")),
    path("", include("apps.companies.urls")),
    path("", include("apps.btp_catalog.urls")),
    path("", include("apps.opportunities.urls")),
    path("", include("apps.applications.urls")),
    path("", include("apps.subscriptions.urls")),
    path("", include("apps.payments.urls")),
    path("", include("apps.notifications.urls")),
    path("", include("apps.activities.urls")),
    path("", include("common.urls")),
]

urlpatterns = [
    path("health/", health, name="health"),
    path("health/ready/", readiness, name="health-ready"),
    path("api/v1/", include((api_v1, "v1"))),
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="api-schema"),
        name="api-docs",
    ),
    path("admin/", admin.site.urls),
    # Toute adresse d'API inconnue répond en JSON (jamais la page de l'application
    # React, qui donnerait un code 200 trompeur à un client d'API).
    path("api/<path:path>", api_not_found, name="api-not-found"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    urlpatterns += [path("<path:path>", spa_fallback, name="spa-fallback")]
    urlpatterns += [path("", spa_fallback)]
