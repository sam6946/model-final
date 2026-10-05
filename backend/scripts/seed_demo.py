"""Jeu de démonstration KEMTA — utilisé par `manage.py seed_kemta --demo`.

Objectif : disposer d'un environnement crédible pour la recette, les captures
d'écran commerciales et les démonstrations client. Les données imitent de vrais
dossiers camerounais (villes, quartiers, montants en FCFA, entreprises, marchés).

Le script passe par les **services métier** partout où ils existent : le jeu de
démonstration valide donc aussi la logique applicative (création d'entreprise,
candidature, projet issu d'une demande, contrat d'entretien, preuve terrain,
abonnement, paiement). C'est volontaire : une donnée de démonstration qui
contourne le code ne prouve rien.
"""
from __future__ import annotations

import io
import logging
from datetime import timedelta
from decimal import Decimal

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger("kemta.demo")

DEMO_PREFIX = "+237600"

COMPANIES = [
    {
        "name": "BTP Sawa Construction SARL",
        "city": "Douala", "region": "LITTORAL", "years": 12, "employees": 34, "projects": 58,
        "phone": DEMO_PREFIX + "000101",
        "description": (
            "Entreprise générale de bâtiment basée à Bonanjo depuis 2012. Gros œuvre, second œuvre "
            "et finitions pour villas, immeubles et locaux professionnels à Douala et Yaoundé."
        ),
        "specialties": ["GROS_OEUVRE", "FONDATIONS", "CARRELAGE", "PEINTURE"],
        "regions": ["LITTORAL", "CENTRE", "OUEST"],
        "registration": "RC/DLA/2012/B/1234", "tax": "M021234567890A",
    },
    {
        "name": "Ambassa Électricité & Réseaux",
        "city": "Yaoundé", "region": "CENTRE", "years": 9, "employees": 18, "projects": 74,
        "phone": DEMO_PREFIX + "000102",
        "description": (
            "Spécialiste des installations électriques basse tension, groupes électrogènes et "
            "domotique résidentielle. Mise aux normes et dépannages d'urgence 7j/7 à Yaoundé."
        ),
        "specialties": ["ELECTRICITE", "CLIMATISATION", "SECURITE_INCENDIE"],
        "regions": ["CENTRE", "LITTORAL"],
        "registration": "RC/YAO/2015/B/4471", "tax": "M031415926535B",
    },
    {
        "name": "Kribi Plomberie & Forage",
        "city": "Kribi", "region": "SUD", "years": 7, "employees": 12, "projects": 41,
        "phone": DEMO_PREFIX + "000103",
        "description": (
            "Forages, châteaux d'eau, réseaux de plomberie et traitement d'eau pour hôtels, "
            "résidences et entreprises de la région du Sud."
        ),
        "specialties": ["PLOMBERIE", "FORAGE", "ASSAINISSEMENT"],
        "regions": ["SUD", "LITTORAL"],
        "registration": "RC/KRI/2017/B/0912", "tax": "M041592653589C",
    },
    {
        "name": "Bafoussam Toiture & Étanchéité",
        "city": "Bafoussam", "region": "OUEST", "years": 15, "employees": 26, "projects": 96,
        "phone": DEMO_PREFIX + "000104",
        "description": (
            "Charpentes métalliques, couvertures et étanchéité de toitures-terrasses. "
            "Interventions sur immeubles résidentiels et équipements publics dans l'Ouest."
        ),
        "specialties": ["CHARPENTE", "ETANCHEITE", "METALLERIE"],
        "regions": ["OUEST", "NORD-OUEST", "LITTORAL"],
        "registration": "RC/BFS/2009/A/0233", "tax": "M051234567890D",
    },
    {
        "name": "Douala Finitions & Décoration",
        "city": "Douala", "region": "LITTORAL", "years": 5, "employees": 15, "projects": 33,
        "phone": DEMO_PREFIX + "000105",
        "description": (
            "Finitions haut de gamme : carrelage grand format, menuiserie aluminium, peinture "
            "décorative et agencement intérieur pour villas et bureaux."
        ),
        "specialties": ["CARRELAGE", "MENUISERIE_ALU", "PEINTURE", "MENUISERIE_BOIS"],
        "regions": ["LITTORAL", "CENTRE"],
        "registration": "RC/DLA/2019/B/7788", "tax": "M061818181818E",
    },
    {
        "name": "Nord Bâtiment Garoua",
        "city": "Garoua", "region": "NORD", "years": 11, "employees": 22, "projects": 52,
        "phone": DEMO_PREFIX + "000106",
        "description": (
            "Construction de bâtiments administratifs, écoles et logements sociaux dans le Nord "
            "et l'Extrême-Nord, avec une équipe de maîtrise d'œuvre locale."
        ),
        "specialties": ["GROS_OEUVRE", "VOIRIE", "DEMOLITION", "ARCHITECTURE"],
        "regions": ["NORD", "EXTRÊME-NORD", "ADAMAOUA"],
        "registration": "RC/GAR/2013/B/3344", "tax": "M071717171717F",
    },
]

REALIZATIONS = [
    ("BTP Sawa Construction SARL", "Villa R+1 de 320 m² — Bonapriso", "VILLA", 320, 2025, 95_000_000,
     "Construction complète en 11 mois : fondations, structure, second œuvre et finitions livrées clés en main."),
    ("BTP Sawa Construction SARL", "Immeuble R+2 de 8 logements — Bonabéri", "IMMEUBLE", 640, 2024, 210_000_000,
     "Immeuble locatif livré avec parking en sous-sol, ascenseur et groupe électrogène."),
    ("BTP Sawa Construction SARL", "Local commercial 180 m² — Akwa", "LOCAL_COMMERCIAL", 180, 2023, 48_000_000,
     "Local commercial sur deux niveaux avec vitrine et mezzanine, livré en 6 mois."),
    ("Ambassa Électricité & Réseaux", "Mise aux normes électriques — immeuble Bastos", "IMMEUBLE", 520, 2025, 34_000_000,
     "Remplacement du tableau général, câblage complet et installation d'un parafoudre sur 7 niveaux."),
    ("Ambassa Électricité & Réseaux", "Groupe électrogène 80 kVA — clinique Odza", "SANTE", 300, 2024, 22_500_000,
     "Installation d'un groupe de secours avec inverseur automatique et salle technique dédiée."),
    ("Kribi Plomberie & Forage", "Forage 120 m + château d'eau — hôtel Kribi", "FORAGE", 0, 2025, 18_000_000,
     "Forage équipé d'une pompe solaire, château d'eau de 10 m³ et réseau de distribution complet."),
    ("Kribi Plomberie & Forage", "Réseau plomberie — 12 appartements", "APPARTEMENT", 980, 2024, 27_000_000,
     "Installation complète : alimentation, évacuation, production d'eau chaude et surpresseurs."),
    ("Bafoussam Toiture & Étanchéité", "Charpente métallique — halle de marché", "AMENAGEMENT", 1_400, 2023, 88_000_000,
     "Charpente de 1 400 m² avec couverture bac acier et évacuation des eaux pluviales."),
    ("Bafoussam Toiture & Étanchéité", "Étanchéité de toiture-terrasse — immeuble 6 niveaux", "IMMEUBLE", 720, 2025, 31_000_000,
     "Réfection complète de l'étanchéité avec relevés, protection gravillonnée et évacuations."),
    ("Douala Finitions & Décoration", "Rénovation intérieure — villa Logbessou", "RENOVATION", 260, 2025, 19_500_000,
     "Carrelage grand format, dressing sur mesure, faux plafonds et peinture décorative."),
    ("Douala Finitions & Décoration", "Agencement de bureaux — 400 m² Makepe", "BUREAU", 400, 2024, 26_000_000,
     "Cloisons vitrées, mobilier sur mesure, éclairage et revêtements acoustiques."),
    ("Nord Bâtiment Garoua", "École primaire de 6 salles — Garoua", "ECOLE", 540, 2024, 74_000_000,
     "Construction de 6 salles de classe, bloc sanitaire et forage pour l'école."),
]

CUSTOMERS = [
    ("Aïcha", "Mbarga", "Douala", "CM", False, "Cheffe d'entreprise, construction d'une villa familiale à Bonapriso."),
    ("Jules", "Etaba", "Montréal", "CA", True, "Investisseur de la diaspora, construit deux immeubles locatifs à Douala."),
    ("Mireille", "Ngono", "Yaoundé", "CM", False, "Propriétaire d'un immeuble de 6 appartements à Bastos."),
    ("Prosper", "Ekane", "Kribi", "CM", False, "Investisseur hôtelier, suit la rénovation de son établissement."),
    ("Sandrine", "Mbappe", "Paris", "FR", True, "Bailleuse à distance, trois appartements à Yaoundé."),
    ("Ibrahim", "Kouam", "Bafoussam", "CM", False, "Jeune propriétaire, construction d'une maison d'habitation."),
]

PROJECTS = [
    ("Aïcha Mbarga", "Villa familiale Bonapriso — 4 chambres", "BUILD", "IN_PROGRESS", 42, "ON_TRACK",
     "Bonapriso, Douala", 35_000_000, 14_800_000),
    ("Jules Etaba", "Immeuble locatif Makepe — 6 logements", "BUILD", "IN_PROGRESS", 28, "WATCH",
     "Makepe, Douala", 145_000_000, 52_000_000),
    ("Mireille Ngono", "Rénovation cour & façade — Bastos", "MAINTENANCE", "IN_PROGRESS", 65, "ON_TRACK",
     "Bastos, Yaoundé", 18_500_000, 11_900_000),
    ("Prosper Ekane", "Rénovation des 12 chambres — établissement Kribi", "BUILD", "IN_PROGRESS", 55, "AT_RISK",
     "Kribi centre", 62_000_000, 38_500_000),
    ("Sandrine Mbappe", "Suivi délégué — immeuble Odza", "FOLLOW_UP", "IN_PROGRESS", 34, "WATCH",
     "Odza, Yaoundé", 96_000_000, 41_000_000),
    ("Ibrahim Kouam", "Maison d'habitation Bafoussam — 3 chambres", "BUILD", "COMPLETED", 100, "ON_TRACK",
     "Quartier Tougang, Bafoussam", 24_000_000, 23_450_000),
]

OPPORTUNITIES = [
    ("Construction d'un immeuble R+3 à Douala — 12 logements", "IMMEUBLE", "Makepe, Douala", 320_000_000, 420_000_000,
     "OPEN", 5, True, ["GROS_OEUVRE", "FONDATIONS"], 540),
    ("Mise aux normes électriques — 3 sites hospitaliers à Yaoundé", "SANTE", "Yaoundé", 45_000_000, 60_000_000,
     "OPEN", 3, True, ["ELECTRICITE", "SECURITE_INCENDIE"], 120),
    ("Forage et château d'eau — résidence hôtelière à Kribi", "FORAGE", "Kribi", 15_000_000, 22_000_000,
     "OPEN", 2, False, ["FORAGE", "PLOMBERIE"], 90),
    ("Réfection de toitures — groupe scolaire de Bafoussam", "ECOLE", "Bafoussam", 38_000_000, 47_000_000,
     "OPEN", 5, True, ["CHARPENTE", "ETANCHEITE"], 150),
    ("Finitions haut de gamme — villa de 400 m² à Bonanjo", "VILLA", "Bonanjo, Douala", 55_000_000, 72_000_000,
     "REVIEWING", 3, False, ["CARRELAGE", "MENUISERIE_ALU", "PEINTURE"], 180),
]

# Répartition géographique des quartiers par ville (repris du référentiel).
PROPERTIES = [
    ("Mireille Ngono", "Immeuble Bastos — 6 appartements", "IMMEUBLE", "RENTED", "Bastos, Yaoundé", 6, 6, 420, 640_000_000),
    ("Jules Etaba", "Immeuble Makepe — 6 logements", "IMMEUBLE", "RENTED", "Makepe, Douala", 6, 6, 380, 520_000_000),
    ("Sandrine Mbappe", "Résidence Odza — 3 appartements", "APPARTEMENT", "RENTED", "Odza, Yaoundé", 9, 6, 260, 285_000_000),
    ("Prosper Ekane", "Immeuble de rapport Akwa", "IMMEUBLE", "RENTED", "Akwa, Douala", 8, 8, 460, 610_000_000),
    ("Aïcha Mbarga", "Villa Bonapriso (résidence principale)", "VILLA", "OCCUPIED_OWNER", "Bonapriso, Douala", 7, 4, 320, 240_000_000),
    ("Ibrahim Kouam", "Maison Tougang (location)", "MAISON", "VACANT", "Tougang, Bafoussam", 4, 2, 140, 62_000_000),
]

REVIEWS = [
    ("BTP Sawa Construction SARL", "Achille Fotso", 5, "Chantier livré dans les délais, équipe sérieuse et propre. Les rapports hebdomadaires étaient précis."),
    ("Ambassa Électricité & Réseaux", "Mireille Ngono", 5, "Intervention rapide sur mon immeuble, travail soigné et conforme aux normes."),
    ("Kribi Plomberie & Forage", "Prosper Ekane", 4, "Forage fonctionnel et bien dimensionné. Délai légèrement dépassé mais résultat à la hauteur."),
    ("Bafoussam Toiture & Étanchéité", "Ibrahim Kouam", 5, "Étanchéité refaite sans mauvaise surprise, deux saisons de pluies sans fuite."),
    ("Douala Finitions & Décoration", "Aïcha Mbarga", 5, "Finitions impeccables, conseils utiles et respect du budget annoncé."),
    ("Nord Bâtiment Garoua", "Prosper Ekane", 4, "Bonne maîtrise du chantier malgré les contraintes de saison des pluies."),
]


def _placeholder_image(name: str, label: str) -> ContentFile:
    """Visuel neutre des couleurs KEMTA (remplacé par les photos définitives).

    On évite ainsi toute image cassée dans un environnement de démonstration :
    un aplat de marque vaut mieux qu'un carré blanc troué.
    """
    try:
        from PIL import Image, ImageDraw
    except ImportError:  # Pillow absent : on renvoie un fichier minimal
        return ContentFile(b"", name=name)

    width, height = 1600, 1000
    image = Image.new("RGB", (width, height), (6, 59, 92))
    draw = ImageDraw.Draw(image)
    for index in range(0, width, 80):
        draw.line([(index, 0), (index - 400, height)], fill=(8, 72, 110), width=2)
    draw.rectangle([(0, height - 260), (width, height)], fill=(32, 160, 75))
    draw.rectangle([(60, 60), (60 + 220, 66)], fill=(255, 255, 255))
    draw.text((80, height - 190), label[:60], fill=(255, 255, 255))
    buffer = io.BytesIO()
    image.save(buffer, format="WEBP", quality=82, method=4)
    return ContentFile(buffer.getvalue(), name=name)


def _asset(name: str, *, label: str, uploaded_by=None, kind: str = "IMAGE"):
    """Crée (ou récupère) un Asset de démonstration, fichier compris."""
    from common.models import Asset

    asset = Asset.objects.filter(original_filename=name).first()
    if asset is not None:
        return asset

    from apps.evidences.models import Evidence  # noqa: F401  (garantit l'ordre de chargement)

    from common.services.uploads import process_image_variants
    from common.storage import object_storage

    key = f"demo/{name}"
    content = _placeholder_image(name, label)
    object_storage.put(key, io.BytesIO(content.read()), "image/webp", public=True)
    processed = process_image_variants(key=key, mime_type="image/webp")

    asset = Asset.objects.create(
        kind=kind,
        status="READY",
        key=key,
        original_filename=name,
        mime_type="image/webp",
        size_bytes=len(content.read()),
        width=processed.get("width") or 1600,
        height=processed.get("height") or 1000,
        is_public=True,
        uploaded_by=uploaded_by,
        variants=processed.get("variants") or {},
        metadata={"demo": True, "label": label},
    )
    return asset


@transaction.atomic
def seed_demo_data(*, stdout=None) -> str:
    """Crée le jeu de démonstration complet et renvoie un résumé lisible."""
    from django.contrib.auth import get_user_model

    from apps.applications.models import Application
    from apps.applications.services import review_application, submit_application
    from apps.btp_catalog.models import Realization, RealizationMedia
    from apps.companies.models import Company, CompanyMember, CompanyReview, Specialty
    from apps.companies.services import create_company, verify_company
    from apps.evidences.services import create_evidence, review_evidence
    from apps.maintenance.services import complete_visit, create_contract, report_issue
    from apps.notifications.services import notify
    from apps.opportunities.models import Opportunity, OpportunityStatus
    from apps.payments.services import confirm_payment, create_subscription_invoice, initiate_payment
    from apps.projects.services import create_project_from_request, create_task, update_progress
    from apps.properties.models import Property
    from apps.reports.models import DailyReport, PeriodicReport
    from apps.service_requests.models import ServiceRequest
    from apps.service_requests.services import create_service_request
    from apps.subscriptions.models import Plan
    from apps.subscriptions.services import subscribe_company
    from common.constants import NotificationType

    User = get_user_model()
    now = timezone.now()
    today = timezone.localdate()
    log = (lambda message: stdout.write(message)) if stdout else (lambda message: logger.info(message))

    # ---------------------------------------------------------------- équipe
    def team_user(phone: str, first: str, last: str, role: str, city: str = "Douala"):
        user, created = User.objects.get_or_create(
            phone=phone,
            defaults={
                "first_name": first, "last_name": last, "role": role, "city": city,
                "phone_verified": True, "is_staff": role in {"ADMIN", "MANAGER"},
                "is_superuser": role == "ADMIN",
            },
        )
        if created:
            user.set_password("Kemta!2026demo")
            user.save()
        return user

    admin = team_user(DEMO_PREFIX + "000001", "Serge", "Nkoulou", "ADMIN")
    managers = [
        team_user(DEMO_PREFIX + "000002", "Clarisse", "Etoundi", "MANAGER"),
        team_user(DEMO_PREFIX + "000003", "Bertrand", "Kamdem", "MANAGER"),
    ]
    technicians = [
        team_user(DEMO_PREFIX + "000010", "Éric", "Bilong", "FIELD"),
        team_user(DEMO_PREFIX + "000011", "Rodrigue", "Tchoumi", "FIELD"),
        team_user(DEMO_PREFIX + "000012", "Nadège", "Ateba", "FIELD"),
    ]

    # --------------------------------------------------------------- clients
    customers = {}
    for index, (first, last, city, country, diaspora, _note) in enumerate(CUSTOMERS):
        phone = DEMO_PREFIX + f"0002{index:02d}"
        user, created = User.objects.get_or_create(
            phone=phone,
            defaults={
                "first_name": first, "last_name": last, "city": city, "country": country,
                "role": "CUSTOMER", "phone_verified": True,
            },
        )
        if created:
            user.set_password("Kemta!2026demo")
            user.save()
        profile = getattr(user, "customer_profile", None)
        if profile is not None and diaspora:
            profile.is_diaspora = True
            profile.residence_country = country
            profile.save(update_fields=["is_diaspora", "residence_country", "updated_at"])
        customers[f"{first} {last}"] = user

    # ----------------------------------------------------------- entreprises
    specialties = {s.code: s for s in Specialty.objects.all()}
    companies: dict[str, Company] = {}
    for index, spec in enumerate(COMPANIES):
        owner = team_user(
            spec["phone"], spec["name"].split()[0].title(), "Dirigeant", "COMPANY", spec["city"]
        )
        company = Company.objects.filter(owner=owner).first()
        if company is None:
            company = create_company(
                owner=owner,
                data={
                    "name": spec["name"], "description": spec["description"], "city": spec["city"],
                    "region": spec["region"], "phone": spec["phone"],
                    "email": f"contact@{spec['name'].split()[0].lower()}.cm",
                    "registration_number": spec["registration"], "tax_number": spec["tax"],
                    "years_experience": spec["years"], "employees_count": spec["employees"],
                    "projects_count": spec["projects"], "intervention_regions": spec["regions"],
                    "equipment_summary": "Bétonnières, échafaudages, camion benne, outillage électroportatif.",
                },
                specialties=[specialties[code].pk for code in spec["specialties"] if code in specialties],
            )
        companies[spec["name"]] = company
        _asset(f"logo-{company.slug}.webp", label=spec["name"], kind="IMAGE")
        cover = _asset(f"cover-{company.slug}.webp", label=f"{spec['city']} — chantier", uploaded_by=owner)
        company.logo = _asset(f"logo-{company.slug}.webp", label=spec["name"])
        company.cover = cover
        company.save(update_fields=["logo", "cover", "updated_at"])

    # Pièces administratives validées par KEMTA (obligatoires pour la vérification)
    from apps.companies.models import CompanyDocument

    for index, (name, company) in enumerate(companies.items()):
        spec = COMPANIES[index]
        registry_asset = _asset(
            f"rccm-{company.slug}.webp", label=f"Registre de commerce — {name}", uploaded_by=company.owner
        )
        tax_asset = _asset(
            f"contribuable-{company.slug}.webp", label=f"Attestation contribuable — {name}", uploaded_by=company.owner
        )
        CompanyDocument.objects.get_or_create(
            company=company, kind="RCCM",
            defaults={
                "title": "Registre de commerce et du crédit mobilier",
                "asset": registry_asset, "reference_number": spec["registration"],
                "issued_at": today - timedelta(days=400),
                "status": "APPROVED", "review_notes": "Document conforme, numéro vérifié au greffe.",
                "reviewed_at": now - timedelta(days=30), "uploaded_by": company.owner,
            },
        )
        CompanyDocument.objects.get_or_create(
            company=company, kind="TAX_CLEARANCE",
            defaults={
                "title": "Attestation de non-redevance fiscale",
                "asset": tax_asset, "reference_number": spec["tax"],
                "issued_at": today - timedelta(days=60), "expires_at": today + timedelta(days=305),
                "status": "APPROVED", "review_notes": "Attestation en cours de validité.",
                "reviewed_at": now - timedelta(days=20), "uploaded_by": company.owner,
            },
        )

    # --------------------------------------------- réalisations & catalogue
    for name, title, kind, surface, year, budget, description in REALIZATIONS:
        company = companies[name]
        realization = Realization.objects.filter(company=company, title=title).first()
        if realization is None:
            realization = Realization.objects.create(
                company=company, created_by=company.owner, title=title, realization_type=kind,
                description=description, location_text=company.city, country="CM", year=year,
                surface_m2=surface or None, duration_days=int(surface / 3) if surface else 120,
                budget_xaf=Decimal(budget), budget_visible=False, client_name="Client particulier",
                status="PUBLISHED", is_featured=budget > 50_000_000, order=1,
            )
            realization.services.set(company.specialties.all()[:4])
        cover = _asset(
            f"realisation-{realization.pk}.webp", label=title, uploaded_by=company.owner
        )
        before = _asset(f"realisation-{realization.pk}-avant.webp", label=f"{title} — avant")
        after = _asset(f"realisation-{realization.pk}-apres.webp", label=f"{title} — après")
        realization.cover = cover
        realization.save(update_fields=["cover", "updated_at"])
        RealizationMedia.objects.get_or_create(
            realization=realization, asset=cover,
            defaults={"kind": "PHOTO", "caption": title, "order": 1},
        )
        RealizationMedia.objects.get_or_create(
            realization=realization, asset=before,
            defaults={"kind": "BEFORE", "caption": "Avant travaux", "order": 2},
        )
        RealizationMedia.objects.get_or_create(
            realization=realization, asset=after,
            defaults={"kind": "AFTER", "caption": "Après travaux", "order": 3},
        )

    for name, author_name, rating, comment in REVIEWS:
        company = companies[name]
        author = customers.get(author_name) or admin
        CompanyReview.objects.get_or_create(
            company=company, author=author,
            defaults={
                "rating": rating, "comment": comment, "is_published": True,
                "work_quality": rating, "deadline_respect": max(3, rating - 1),
                "communication": rating,
            },
        )
        company.recalculate_rating()

    # Vérification KEMTA (après complétude : le service refuse un dossier vide)
    for company in companies.values():
        if company.verification_status != "VERIFIED":
            verify_company(
                company=company, actor=admin, decision="VERIFIED",
                notes="Pièces contrôlées, références chantier vérifiées sur site.",
            )

    # ---------------------------------------------------------- propriétés
    properties: dict[str, Property] = {}
    for index, (owner_name, name, kind, occupancy, location, rooms, baths, surface, value) in enumerate(PROPERTIES):
        owner = customers.get(owner_name)
        prop = Property.objects.filter(owner=owner, name=name).first()
        if prop is None:
            prop = Property.objects.create(
                owner=owner, manager=managers[index % len(managers)], name=name,
                property_type=kind, occupancy_status=occupancy,
                city=location.split(",")[-1].strip(), location_text=location, country="CM",
                rooms_count=rooms, bathrooms_count=baths, area_m2=surface,
                land_area_m2=surface * 2, levels_count=2 if "IMMEUBLE" in kind else 1,
                estimated_value_xaf=Decimal(value), year_built=2012 + index,
                condition_score=78 - index, last_visited_at=now - timedelta(days=30 + index * 5),
                documentation_status="COMPLETE" if index % 2 == 0 else "PARTIAL",
                title_deed_number=f"TF-{1200 + index}/DLA" if index % 2 == 0 else "",
                monthly_rent_xaf=Decimal(180_000 + index * 40_000) if occupancy == "RENTED" else None,
                tenant_name="Locataire en place" if occupancy == "RENTED" else "",
                has_water=True, has_electricity=True, is_fenced=True,
                description=(
                    f"{name} — bien suivi par KEMTA : visites régulières, carnet d'entretien numérique "
                    "et alertes en cas d'anomalie détectée."
                ),
            )
        properties[name] = prop
        photo = _asset(f"propriete-{prop.pk}.webp", label=name, uploaded_by=owner)
        prop.cover = photo
        prop.save(update_fields=["cover", "updated_at"])

    # ------------------------------------------- demandes de service → projets
    manager = managers[0]
    customer_projects: dict[str, object] = {}
    for index, (customer_name, name, kind, status, progress, health, location, budget, spent) in enumerate(PROJECTS):
        customer = customers.get(customer_name)
        project = customer.projects.filter(name=name).first() if customer else None
        if project is None:
            request = create_service_request(
                data={
                    "kind": "BUILD_PROJECT" if kind == "BUILD" else "EXISTING_SITE",
                    "first_name": customer.first_name, "last_name": customer.last_name,
                    "phone": customer.phone, "email": customer.email or "",
                    "city": location.split(",")[-1].strip(), "location_text": location,
                    "country": customer.country, "property_type": "IMMEUBLE" if "immeuble" in name.lower() else "VILLA",
                    "budget_min_xaf": Decimal(budget) * Decimal("0.85"), "budget_max_xaf": Decimal(budget),
                    "surface_m2": 250 + index * 40, "description": f"Projet de référence : {name}.",
                    "terms_accepted": True, "requirements": ["suivi_chantier", "controle_budget"],
                    "has_land": True,
                },
                user=customer,
            )
            from apps.service_requests.services import change_status

            change_status(
                service_request=request, new_status="QUALIFIED", actor=manager,
                comment="Dossier complet, visite de site planifiée.",
            )
            project = create_project_from_request(
                service_request=request, actor=manager,
                overrides={
                    "name": name, "kind": kind, "budget_total_xaf": Decimal(budget),
                    "manager": manager.pk, "status": status, "health": health,
                    "location_text": location, "planned_start": today - timedelta(days=120),
                    "planned_end": today + timedelta(days=180 - index * 20),
                    "actual_start": today - timedelta(days=110), "contract_signed": True,
                },
            )
        project.physical_progress = Decimal(progress)
        project.budget_spent_xaf = Decimal(spent)
        if status == "COMPLETED":
            project.actual_end = today - timedelta(days=15)
            project.completed_at = now - timedelta(days=15)
        project.save()
        customer_projects[name] = project

        # Preuves terrain validées (avec quelques preuves en attente)
        for step in range(1, 4):
            phase = project.phases.order_by("order").first()
            evidence = create_evidence(
                actor=technicians[(index + step) % len(technicians)],
                data={
                    "project": project.pk,
                    "phase": phase.pk if phase else None,
                    "kind": "PHOTO",
                    "title": f"Étape {step} — {name}",
                    "caption": [
                        "Fondations coulées et vérifiées.",
                        "Élévation des murs au niveau R+1.",
                        "Pose des menuiseries et contrôle des niveaux.",
                    ][step - 1],
                    "captured_at": now - timedelta(days=step * 9),
                    "latitude": Decimal("4.0511") + Decimal(step) / 100,
                    "longitude": Decimal("9.7679") + Decimal(step) / 100,
                    "asset": _asset(f"preuve-{project.pk}-{step}.webp", label=f"{name} — étape {step}").pk,
                    "is_visible_to_customer": True,
                },
            )
            if step < 3:
                review_evidence(evidence=evidence, action="VALIDATE", reviewer=manager,
                                comment="Conforme au planning, preuve horodatée.")

        create_task(
            project=project, actor=manager,
            data={
                "title": "Contrôle des fers avant coulage",
                "description": "Vérifier diamètres, recouvrements et enrobage avant le coulage de la dalle.",
                "status": "IN_PROGRESS", "priority": "HIGH",
                "assignee": technicians[index % len(technicians)].pk,
                "due_date": today + timedelta(days=3),
            },
        )
        DailyReport.objects.get_or_create(
            project=project, report_date=today - timedelta(days=2),
            defaults={
                "created_by": technicians[index % len(technicians)],
                "works_done": "Coulage de la dalle haute, décoffrage partiel et évacuation des gravats.",
                "works_planned": "Montage des cloisons, passage des gaines électriques.",
                "workers_count": 14 + index, "supervisors_count": 2, "hours_worked": 9,
                "weather": "Ensoleillé", "progress_percent": progress,
                "is_visible_to_customer": True, "validated_by": manager, "validated_at": now - timedelta(days=1),
            },
        )
        PeriodicReport.objects.get_or_create(
            project=project, period="WEEKLY", period_start=today - timedelta(days=7),
            defaults={
                "period_end": today, "title": f"Rapport hebdomadaire — {name}",
                "summary": (
                    f"Avancement à {progress} % du planning. Les postes gros œuvre sont conformes, "
                    "les livraisons de matériaux sont arrivées à temps."
                ),
                "progress_snapshot": {"physical": progress, "budget_used": round(spent / budget * 100, 1)},
                "financial_summary": {"planned": float(budget), "spent": float(spent)},
                "highlights": ["Dalle coulée", "Contrôle qualité sans réserve"],
                "risks": ["Approvisionnement en carrelage à confirmer"],
                "next_steps": ["Montage des cloisons", "Commande des menuiseries"],
                "status": "SENT", "created_by": manager, "sent_at": now - timedelta(days=1),
                "generated_at": now - timedelta(days=1),
            },
        )

    # ------------------------------------------------------------ entretien
    from apps.maintenance.models import MaintenanceServiceType

    service_types = list(MaintenanceServiceType.objects.order_by("order"))
    for index, (owner_name, name, *_rest) in enumerate(PROPERTIES[:4]):
        customer = customers[owner_name]
        prop = properties[name]
        if prop.maintenance_contracts.exists():
            continue
        contract = create_contract(
            customer=customer,
            actor=manager,
            data={
                "property": prop.pk, "frequency": "QUARTERLY",
                "services": [s.pk for s in service_types[:3]],
                "start_date": today - timedelta(days=90), "visits_included": 4,
                "notes": "Entretien préventif trimestriel — carnet numérique tenu par KEMTA.",
            },
        )
        visit = contract.visits.order_by("scheduled_for").first()
        if visit and visit.status in {"SCHEDULED", "CONFIRMED"}:
            complete_visit(
                visit=visit, actor=technicians[index % len(technicians)],
                report="Visite préventive réalisée : réseaux, étanchéité et menuiseries contrôlés.",
                score=82 - index,
            )
        report_issue(
            prop=prop, actor=customers[owner_name],
            data={
                "title": "Infiltrations sous la terrasse",
                "description": "Traces d'humidité apparues au plafond du dernier niveau après les pluies.",
                "severity": "HIGH" if index == 0 else "MEDIUM",
                "estimate_xaf": Decimal(350_000 + index * 120_000),
            },
        )

    # -------------------------------------------------- espaces entreprises
    plan_by_code = {plan.code: plan for plan in Plan.objects.all()}
    for index, (company_name, company) in enumerate(companies.items()):
        subscription = company.subscriptions.first()
        if subscription is None and "FREE" in plan_by_code:
            try:
                subscription = subscribe_company(
                    company=company, plan=plan_by_code["FREE"], actor=company.owner, provider="MANUAL"
                )
            except ValueError:
                subscription = None
        if subscription is not None and index % 3 == 0 and "PRO" in plan_by_code:
            try:
                subscription = subscribe_company(
                    company=company, plan=plan_by_code["PRO"], actor=company.owner, provider="MTN_MOMO"
                )
            except ValueError:
                pass
        if (
            subscription is not None
            and (subscription.plan.price_xaf or 0) > 0
            and subscription.status in {"TRIALING", "ACTIVE"}
        ):
            invoice = subscription.invoices.first() or create_subscription_invoice(
                subscription=subscription, actor=admin
            )
            if not invoice.payments.filter(status="SUCCEEDED").exists() and index % 2 == 0:
                payment = initiate_payment(
                    kind="INVOICE", provider="MTN_MOMO", amount_xaf=invoice.total_xaf,
                    actor=company.owner, company=company, invoice=invoice, subscription=subscription,
                    payer_phone=company.phone, idempotency_key=f"demo-invoice-{invoice.pk}",
                )
                confirm_payment(payment=payment, actor=admin)

    # ------------------------------------------------------- opportunités
    opportunities: list[Opportunity] = []
    for (
        title, kind, location, budget_min, budget_max, status, min_years, requires_verified,
        specialty_codes, duration,
    ) in OPPORTUNITIES:
        opportunity = Opportunity.objects.filter(title=title).first()
        if opportunity is None:
            opportunity = Opportunity.objects.create(
                title=title, description=(
                    f"Marché privé publié par KEMTA : {title}. Dossier technique disponible après "
                    "candidature ; visite de site possible sur rendez-vous."
                ),
                property_type=kind, location_text=location, country="CM",
                budget_min_xaf=Decimal(budget_min), budget_max_xaf=Decimal(budget_max),
                budget_visible=True, start_date=today + timedelta(days=30), duration_days=duration,
                application_deadline=today + timedelta(days=21 + len(opportunities) * 5),
                minimum_experience_years=min_years, requires_verified_company=requires_verified,
                status=OpportunityStatus.OPEN if status == "OPEN" else OpportunityStatus.REVIEWING,
                visibility="PUBLIC", is_featured=budget_max > 100_000_000,
                published_at=now - timedelta(days=5 + len(opportunities)),
                created_by=admin, site_available_for_visit=True,
                scope_of_work="Travaux décrits au dossier technique remis aux entreprises présélectionnées.",
                required_documents=["RCCM", "Attestation de non-redevance", "Références de chantier"],
            )
            opportunity.required_specialties.set(
                [specialties[code] for code in specialty_codes if code in specialties]
            )
        opportunities.append(opportunity)

    # ------------------------------------------------------- candidatures
    for index, opportunity in enumerate(opportunities[:4]):
        company = list(companies.values())[index % len(companies)]
        if Application.objects.filter(opportunity=opportunity, company=company).exists():
            continue
        try:
            application = submit_application(
                opportunity=opportunity, company=company, submitted_by=company.owner,
                data={
                    "presentation": (
                        f"{company.name}, {company.years_experience} ans d'expérience et "
                        f"{company.projects_count} chantiers livrés. Équipe de {company.employees_count} "
                        "personnes, matériel en propre, capacité à démarrer sous 30 jours."
                    ),
                    "similar_experience": "Références vérifiables sur des projets comparables à Douala et Yaoundé.",
                    "methodology": (
                        "Installation de chantier, fondations, structure, second œuvre puis finitions, "
                        "avec un contrôle qualité par étape et un rapport hebdomadaire KEMTA."
                    ),
                    "estimated_budget_xaf": opportunity.budget_max_xaf * Decimal("0.92"),
                    "proposed_duration_days": opportunity.duration_days,
                    "team_size": company.employees_count,
                    "team_composition": "Conducteurs de travaux, chefs d'équipe, ouvriers qualifiés",
                    "accepts_site_visit": True,
                },
            )
            if index == 0:
                review_application(
                    application=application, reviewer=manager,
                    data={
                        "status": "SHORTLISTED", "score": Decimal("84"),
                        "internal_notes": "Dossier complet, références solides, trésorerie à confirmer.",
                        "client_feedback": "Entreprise présélectionnée pour la visite de site.",
                    },
                )
            elif index == 1:
                review_application(
                    application=application, reviewer=manager,
                    data={
                        "status": "AWARDED", "score": Decimal("91"),
                        "internal_notes": "Meilleure offre technique et prix cohérent.",
                        "client_feedback": "Marché attribué.",
                    },
                )
        except (ValueError, PermissionError) as exc:  # pragma: no cover - dépend des données
            logger.warning("demo_application_skipped", extra={"reason": str(exc)[:160]})

    # -------------------------------------------------------- notifications
    for customer in list(customers.values())[:3]:
        notify(
            recipient=customer,
            notification_type=NotificationType.PROJECT,
            title="Nouvelle preuve terrain disponible",
            body="Votre chargé de suivi a publié des photos de l'avancement : consultez-les dans votre espace.",
            action_url="/espace/projets",
            action_label="Voir les preuves",
            dedupe_key=f"demo:evidence:{customer.pk}",
        )

    summary = (
        f"{len(companies)} entreprises vérifiées, {len(REALIZATIONS)} réalisations, "
        f"{len(customer_projects)} projets suivis, {len(properties)} propriétés, "
        f"{len(opportunities)} marchés, {len(customers) + len(COMPANIES) + 6} comptes"
    )
    log(f"    – {summary}")
    return summary
