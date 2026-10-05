"""API des entreprises BTP : catalogue public, espace entreprise, vérification."""
from __future__ import annotations

from django.db.models import Count, Prefetch, Q
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from apps.btp_catalog.models import Realization
from apps.companies.models import Company, CompanyDocument, CompanyMember, CompanyReview, Specialty, VerificationStatus
from apps.companies.serializers import (
    CompanyAdminSerializer,
    CompanyDocumentSerializer,
    CompanyMemberSerializer,
    CompanyPublicDetailSerializer,
    CompanyPublicListSerializer,
    CompanyReviewSerializer,
    CompanyVerificationSerializer,
    CompanyWriteSerializer,
    SpecialtySerializer,
)
from apps.companies.services import company_stats, create_company, verify_company
from common.pagination import KemtaPageNumberPagination
from common.permission_codes import Perm
from common.permissions import HasPermission, IsKemtaTeam


class SpecialtyListView(APIView):
    """Corps d'état disponibles (étape 2 de l'onboarding)."""

    permission_classes = [AllowAny]

    def get(self, _request):
        from django.core.cache import cache

        from common.cache import TTL, make_key

        key = make_key("specialties", "v1")
        payload = cache.get(key)
        if payload is None:
            specialties = Specialty.objects.filter(is_active=True).order_by("order", "name")
            payload = SpecialtySerializer(specialties, many=True).data
            cache.set(key, payload, TTL["configuration"])
        grouped: dict[str, list] = {}
        for item in payload:
            grouped.setdefault(item["category"] or "Autres", []).append(item)
        return Response({"results": payload, "grouped": grouped})


class PublicCompanyViewSet(ReadOnlyModelViewSet):
    """Catalogue public des entreprises BTP (aucune authentification)."""

    permission_classes = [AllowAny]
    lookup_field = "slug"
    pagination_class = KemtaPageNumberPagination

    def get_queryset(self):
        queryset = (
            Company.objects.filter(is_published=True, verification_status=VerificationStatus.VERIFIED)
            .prefetch_related(
                Prefetch("specialties", queryset=Specialty.objects.only("id", "code", "name", "icon")),
                Prefetch(
                    "realizations",
                    queryset=Realization.objects.filter(status="PUBLISHED").select_related("cover", "location"),
                ),
                Prefetch("reviews", queryset=CompanyReview.objects.filter(is_published=True).select_related("author")),
            )
            .annotate(realizations_count_cache=Count("realizations", filter=Q(realizations__status="PUBLISHED"), distinct=True))
        )
        params = self.request.query_params
        if params.get("search"):
            search = params["search"]
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(description__icontains=search) | Q(city__icontains=search)
            )
        if params.get("city"):
            queryset = queryset.filter(city__icontains=params["city"])
        if params.get("specialty"):
            queryset = queryset.filter(specialties__code=params["specialty"])
        if params.get("min_experience"):
            try:
                queryset = queryset.filter(years_experience__gte=int(params["min_experience"]))
            except ValueError:
                pass
        if params.get("verified") in {"1", "true"}:
            queryset = queryset.filter(verification_status=VerificationStatus.VERIFIED)
        ordering = params.get("ordering") or "-is_featured"
        if ordering == "rating":
            queryset = queryset.order_by("-rating_average", "-rating_count")
        elif ordering == "experience":
            queryset = queryset.order_by("-years_experience")
        elif ordering == "recent":
            queryset = queryset.order_by("-created_at")
        else:
            queryset = queryset.order_by("-is_featured", "-rating_average", "name")
        return queryset.distinct()

    def get_serializer_class(self):
        if self.action == "retrieve":
            return CompanyPublicDetailSerializer
        return CompanyPublicListSerializer

    def retrieve(self, request, *args, **kwargs):
        company = self.get_object()
        serializer = self.get_serializer(company)
        data = serializer.data
        data["stats"] = {
            "realizations": company.realizations.filter(status="PUBLISHED").count(),
            "years_experience": company.years_experience,
            "projects_count": company.projects_count,
            "rating": float(company.rating_average or 0),
            "rating_count": company.rating_count,
            "verified_since": company.verified_at,
        }
        return Response(data)


class MyCompanyView(APIView):
    """Espace entreprise : création (onboarding) et mise à jour du profil."""

    permission_classes = [IsAuthenticated]

    def _company(self, user) -> Company | None:
        membership = (
            CompanyMember.objects.select_related("company")
            .filter(user=user, is_active=True)
            .order_by("-role")
            .first()
        )
        return membership.company if membership else None

    def get(self, request):
        company = self._company(request.user)
        if company is None:
            return Response({"company": None, "onboarding_required": True})
        data = CompanyPublicDetailSerializer(company, context={"request": request}).data
        data["stats_detail"] = company_stats(company)
        data["members"] = CompanyMemberSerializer(
            company.members.filter(is_active=True).select_related("user"), many=True
        ).data
        data["documents"] = CompanyDocumentSerializer(
            company.documents.select_related("asset"), many=True
        ).data
        data["role"] = (
            company.members.filter(user=request.user).values_list("role", flat=True).first() or "VIEWER"
        )
        return Response({"company": data, "onboarding_required": False})

    def post(self, request):
        """Création (étape 1→3) : refuse une seconde entreprise pour le même compte."""
        if self._company(request.user) is not None:
            return Response(
                {
                    "error": {
                        "code": "company_exists",
                        "message": "Vous avez déjà un profil entreprise KEMTA. Contactez le support "
                                   "pour ajouter une seconde enseigne.",
                    }
                },
                status=status.HTTP_409_CONFLICT,
            )
        serializer = CompanyWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        specialties = [item.pk for item in data.pop("specialties", [])]
        company = create_company(data=data, owner=request.user, specialties=specialties)
        return Response(
            {
                "message": "Votre profil entreprise est créé. Complétez vos documents et vos réalisations.",
                "company": CompanyPublicDetailSerializer(company).data,
                "next_steps": [
                    "Déposez votre registre de commerce et vos attestations",
                    "Publiez au moins 3 réalisations avec photos",
                    "Choisissez un plan d'abonnement pour gagner en visibilité",
                ],
            },
            status=status.HTTP_201_CREATED,
        )

    def patch(self, request):
        company = self._company(request.user)
        if company is None:
            return Response(
                {"error": {"code": "no_company", "message": "Créez d'abord votre profil entreprise."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        membership = company.members.filter(user=request.user).first()
        if membership is None or not membership.can_manage:
            return Response(
                {"error": {"code": "forbidden", "message": "Vous n'avez pas les droits pour modifier ce profil."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = CompanyWriteSerializer(company, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        specialties = data.pop("specialties", None)
        company = serializer.save()
        if specialties is not None:
            company.specialties.set([item.pk for item in specialties])
        from common.cache import invalidate

        invalidate("company_public", company.slug)
        return Response({"message": "Profil mis à jour.", "company": CompanyPublicDetailSerializer(company).data})


class MyCompanyDocumentViewSet(ModelViewSet):
    """Documents administratifs de l'entreprise (étape 4 de l'onboarding)."""

    serializer_class = CompanyDocumentSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    filterset_fields = ["kind", "status"]

    def _company(self):
        membership = CompanyMember.objects.filter(
            user=self.request.user, is_active=True, role__in=["OWNER", "MANAGER", "EDITOR"]
        ).select_related("company").first()
        if membership:
            return membership.company
        membership = CompanyMember.objects.filter(user=self.request.user, is_active=True).select_related("company").first()
        return membership.company if membership else None

    def get_queryset(self):
        # L'équipe KEMTA examine les dossiers de toutes les entreprises : elle ne fait
        # partie d'aucune, donc ce test doit précéder la résolution de l'entreprise.
        if self.request.user.is_kemta_team:
            return CompanyDocument.objects.all().select_related("asset", "company")
        company = self._company()
        if company is None:
            return CompanyDocument.objects.none()
        return CompanyDocument.objects.filter(company=company).select_related("asset")

    def create(self, request, *args, **kwargs):
        company = self._company()
        if company is None:
            return Response(
                {"error": {"code": "no_company", "message": "Créez d'abord votre profil entreprise."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        membership = company.members.filter(user=request.user).first()
        if membership is None or not membership.can_manage:
            return Response(
                {"error": {"code": "forbidden", "message": "Vous n'avez pas les droits pour déposer un document."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = CompanyDocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document = serializer.save(company=company, uploaded_by=request.user, status="PENDING")
        return Response(CompanyDocumentSerializer(document).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="review")
    def review(self, request, pk=None):
        if not request.user.is_kemta_team:
            return Response(
                {"error": {"code": "forbidden", "message": "Seule l'équipe KEMTA peut examiner un document."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        document = self.get_object()
        decision = request.data.get("status")
        if decision not in {"APPROVED", "REJECTED", "PENDING"}:
            return Response(
                {"error": {"code": "invalid", "message": "Décision inconnue (APPROVED, REJECTED ou PENDING)."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from apps.companies.services import review_company_document

        try:
            document = review_company_document(
                document=document, actor=request.user, decision=decision,
                notes=request.data.get("notes") or "",
            )
        except ValueError as exc:
            return Response(
                {"error": {"code": "invalid", "message": str(exc)}}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response(CompanyDocumentSerializer(document).data)


class CompanyReviewViewSet(ModelViewSet):
    """Avis client sur une entreprise (modération KEMTA avant publication)."""

    serializer_class = CompanyReviewSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = KemtaPageNumberPagination
    filterset_fields = ["company", "is_published", "rating"]
    ordering = ["-created_at"]

    def get_queryset(self):
        queryset = CompanyReview.objects.select_related("author", "company")
        if self.request.user.is_kemta_team:
            return queryset
        return queryset.filter(Q(author=self.request.user) | Q(is_published=True))

    def perform_create(self, serializer):
        review = serializer.save(author=self.request.user, is_published=False)
        company = review.company
        from apps.activities.services import record_activity
        from apps.notifications.services import notify
        from common.constants import NotificationType

        record_activity(
            verb="CATALOG_UPDATED",
            message=f"Avis déposé sur {company.name} ({review.rating}/5)",
            actor=self.request.user,
            company=company,
            entity_type="CompanyReview",
            entity_id=review.pk,
            visibility="TEAM",
        )
        notify(
            recipient=company.owner,
            notification_type=NotificationType.SYSTEM,
            title="Nouvel avis client reçu",
            body=f"Un client a laissé un avis de {review.rating}/5 sur {company.name}. Il sera publié après vérification.",
            action_url=f"/entreprise/avis",
            action_label="Voir l'avis",
            entity_type="CompanyReview",
            entity_id=review.pk,
            dedupe_key=f"review:{review.pk}:created",
        )

    @action(detail=True, methods=["post"], url_path="moderate")
    def moderate(self, request, pk=None):
        if not request.user.is_kemta_team:
            return Response(
                {"error": {"code": "forbidden", "message": "Seule l'équipe KEMTA peut publier un avis."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        review = self.get_object()
        publish = bool(request.data.get("publish", True))
        review.is_published = publish
        review.save(update_fields=["is_published"])
        review.company.recalculate_rating()
        return Response(CompanyReviewSerializer(review).data)


class AdminCompanyViewSet(ModelViewSet):
    """Back-office : examen des dossiers d'entreprise et mise en avant."""

    permission_classes = [IsAuthenticated, HasPermission(Perm.VERIFY_COMPANY)]
    serializer_class = CompanyAdminSerializer
    pagination_class = KemtaPageNumberPagination
    filterset_fields = ["verification_status", "is_published", "is_featured", "city", "region"]
    search_fields = ["name", "legal_name", "registration_number", "phone", "owner__phone"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return Company.objects.select_related("owner").annotate(
            documents_count_cache=Count("documents", distinct=True),
            realizations_count_cache=Count("realizations", distinct=True),
        )

    @action(detail=True, methods=["post"], url_path="verify")
    def verify(self, request, pk=None):
        company = self.get_object()
        serializer = CompanyVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            verify_company(
                company=company,
                actor=request.user,
                decision="VERIFIED" if serializer.validated_data["approve"] else "REJECTED",
                notes=serializer.validated_data.get("notes", ""),
            )
        except ValueError as exc:
            return Response(
                {"error": {"code": "incomplete_profile", "message": str(exc)}},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(
            {
                "message": "Entreprise vérifiée et publiée." if serializer.validated_data["approve"]
                else "Dossier renvoyé à l'entreprise pour complément.",
                "company": CompanyAdminSerializer(company).data,
            }
        )

    @action(detail=True, methods=["post"], url_path="feature")
    def feature(self, request, pk=None):
        company = self.get_object()
        company.is_featured = bool(request.data.get("featured", True))
        company.save(update_fields=["is_featured", "updated_at"])
        return Response(CompanyAdminSerializer(company).data)

    @action(detail=False, methods=["get"], url_path="stats")
    def stats(self, request):
        aggregates = Company.objects.aggregate(
            total=Count("id"),
            pending=Count("id", filter=Q(verification_status=VerificationStatus.PENDING)),
            verified=Count("id", filter=Q(verification_status=VerificationStatus.VERIFIED)),
            rejected=Count("id", filter=Q(verification_status=VerificationStatus.REJECTED)),
            published=Count("id", filter=Q(is_published=True)),
        )
        return Response(aggregates)
