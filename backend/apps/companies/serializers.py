"""Serializers des entreprises BTP (onboarding, profil public, vérification)."""
from __future__ import annotations

from rest_framework import serializers

from apps.companies.models import Company, CompanyDocument, CompanyMember, CompanyReview, Specialty
from common.serializers import AssetSerializer


class SpecialtySerializer(serializers.ModelSerializer):
    class Meta:
        model = Specialty
        fields = ("id", "code", "name", "category", "icon")


class CompanyMemberSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.full_name", read_only=True)
    user_phone = serializers.CharField(source="user.phone", read_only=True)
    role_label = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = CompanyMember
        fields = ("id", "user", "user_name", "user_phone", "role", "role_label", "job_title", "is_active", "joined_at")
        read_only_fields = ("joined_at",)


class CompanyDocumentSerializer(serializers.ModelSerializer):
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    asset_detail = AssetSerializer(source="asset", read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = CompanyDocument
        fields = (
            "id", "kind", "kind_label", "title", "asset", "asset_detail", "reference_number",
            "issued_at", "expires_at", "status", "status_label", "review_notes", "reviewed_at",
            "is_expired", "created_at",
        )
        read_only_fields = ("status", "review_notes", "reviewed_at", "created_at")


class CompanyPublicListSerializer(serializers.ModelSerializer):
    """Carte d'entreprise dans le catalogue public."""

    specialities = serializers.SerializerMethodField()
    logo_url = serializers.CharField(read_only=True)
    cover_url = serializers.CharField(read_only=True)
    rating = serializers.FloatField(source="rating_average", read_only=True)
    is_verified = serializers.BooleanField(read_only=True)
    realizations_count = serializers.SerializerMethodField()
    intervention_label = serializers.SerializerMethodField()

    class Meta:
        model = Company
        fields = (
            "id", "name", "slug", "city", "region", "specialities", "years_experience",
            "projects_count", "logo_url", "cover_url", "rating", "rating_count",
            "is_verified", "is_featured", "realizations_count", "description",
            "intervention_label", "employees_count",
        )

    def get_specialities(self, obj: Company) -> list:
        cache = getattr(obj, "specialties_cache", None)
        if cache is None:
            cache = list(obj.specialties.all())
        return [{"code": item.code, "name": item.name, "icon": item.icon} for item in cache]

    def get_realizations_count(self, obj: Company) -> int:
        return getattr(obj, "realizations_count_cache", None) or obj.realizations.filter(
            status="PUBLISHED"
        ).count()

    def get_intervention_label(self, obj: Company) -> str:
        zones = obj.intervention_regions or []
        if not zones:
            return f"{obj.city} et environs"
        return " · ".join(str(zone) for zone in zones[:3])


class CompanyPublicDetailSerializer(CompanyPublicListSerializer):
    """Page publique d'une entreprise : /entreprises/:slug."""

    documents_verified = serializers.SerializerMethodField()
    reviews = serializers.SerializerMethodField()
    completed_projects_count = serializers.IntegerField(read_only=True)
    contact = serializers.SerializerMethodField()
    realizations = serializers.SerializerMethodField()

    class Meta(CompanyPublicListSerializer.Meta):
        fields = CompanyPublicListSerializer.Meta.fields + (
            "legal_name", "address", "website", "equipment_summary", "verification_status",
            "verified_at", "documents_verified", "reviews", "completed_projects_count",
            "intervention_radius_km", "contact", "realizations",
        )

    def get_documents_verified(self, obj: Company) -> int:
        return obj.documents.filter(status="APPROVED").count()

    def get_contact(self, obj: Company) -> dict:
        """Masquage partiel : KEMTA reste l'intermédiaire commercial."""
        return {
            "phone": obj.phone,
            "email": obj.email,
            "city": obj.city,
            "website": obj.website,
            "preferred_channel": "KEMTA",
        }

    def get_reviews(self, obj: Company) -> list:
        reviews = obj.reviews.filter(is_published=True).select_related("author")[:8]
        return [
            {
                "id": review.pk,
                "author": review.author.full_name,
                "author_city": review.author.city,
                "rating": review.rating,
                "comment": review.comment,
                "work_quality": review.work_quality,
                "deadline_respect": review.deadline_respect,
                "communication": review.communication,
                "created_at": review.created_at,
                "response": review.response,
            }
            for review in reviews
        ]

    def get_realizations(self, obj: Company) -> list:
        realizations = obj.realizations.filter(status="PUBLISHED").select_related("cover", "location")[:12]
        return [
            {
                "id": item.pk,
                "title": item.title,
                "slug": item.slug,
                "type": item.realization_type,
                "type_label": item.get_realization_type_display(),
                "location": item.display_location,
                "year": item.year,
                "surface_m2": float(item.surface_m2) if item.surface_m2 else None,
                "cover_url": item.cover_url,
                "budget_display": (
                    f"{int(item.budget_xaf):,} FCFA".replace(",", " ")
                    if item.budget_visible and item.budget_xaf
                    else ""
                ),
                "services": [s.name for s in item.services.all()],
            }
            for item in realizations
        ]


class CompanyWriteSerializer(serializers.ModelSerializer):
    """Étape 1 & 3 de l'onboarding : informations et présentation."""

    specialties = serializers.PrimaryKeyRelatedField(
        queryset=Specialty.objects.filter(is_active=True), many=True, required=False
    )

    class Meta:
        model = Company
        fields = (
            "name", "legal_name", "registration_number", "tax_number", "phone", "secondary_phone",
            "email", "website", "city", "region", "address", "country", "description",
            "years_experience", "employees_count", "projects_count", "equipment_summary",
            "specialties", "intervention_regions", "intervention_radius_km", "logo", "cover",
        )

    def validate_name(self, value: str) -> str:
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Le nom de l'entreprise doit contenir au moins 3 caractères.")
        return value.strip()

    def validate_phone(self, value: str) -> str:
        from common.utils import normalize_phone

        try:
            return normalize_phone(value)
        except ValueError as exc:
            raise serializers.ValidationError(
                "Ce numéro professionnel n'est pas valide. Exemple : +237 6 99 11 22 33."
            ) from exc

    def validate_description(self, value: str) -> str:
        if value and len(value.strip()) < 60:
            raise serializers.ValidationError(
                "Présentez votre entreprise en quelques phrases (60 caractères minimum) : "
                "c'est ce que liront les clients."
            )
        return value

    def validate(self, attrs):
        if self.instance is None and not (attrs.get("phone") and attrs.get("city") and attrs.get("name")):
            raise serializers.ValidationError({
                "name": "Le nom, la ville et le téléphone sont nécessaires pour créer votre profil."
            })
        return attrs


class CompanyAdminSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source="owner.full_name", read_only=True)
    owner_phone = serializers.CharField(source="owner.phone", read_only=True)
    status_label = serializers.CharField(source="get_verification_status_display", read_only=True)
    documents_count = serializers.SerializerMethodField()
    realizations_count = serializers.SerializerMethodField()

    class Meta:
        model = Company
        fields = (
            "id", "name", "slug", "legal_name", "city", "region", "phone", "email",
            "verification_status", "status_label", "verification_notes", "verified_at",
            "is_published", "is_featured", "owner_name", "owner_phone", "years_experience",
            "employees_count", "projects_count", "rating_average", "rating_count",
            "documents_count", "realizations_count", "created_at", "updated_at",
        )

    def get_documents_count(self, obj: Company) -> int:
        return getattr(obj, "documents_count_cache", None) or obj.documents.count()

    def get_realizations_count(self, obj: Company) -> int:
        return getattr(obj, "realizations_count_cache", None) or obj.realizations.count()


class CompanyReviewSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.full_name", read_only=True)

    class Meta:
        model = CompanyReview
        fields = (
            "id", "company", "project", "rating", "comment", "work_quality",
            "deadline_respect", "communication", "is_published", "response", "author_name",
            "created_at",
        )
        read_only_fields = ("is_published", "response", "created_at")

    def validate(self, attrs):
        project = attrs.get("project") or getattr(self.instance, "project", None)
        company = attrs.get("company") or getattr(self.instance, "company", None)
        if project and company and project.company_id != company.pk:
            raise serializers.ValidationError({
                "project": "Le projet choisi n'est pas rattaché à cette entreprise."
            })
        return attrs


class CompanyVerificationSerializer(serializers.Serializer):
    approve = serializers.BooleanField()
    notes = serializers.CharField(required=False, allow_blank=True, max_length=2000)
