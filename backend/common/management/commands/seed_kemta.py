"""Données de référence KEMTA (idempotent, rejouable en production).

Ce que la commande installe :
- le catalogue complet des permissions RBAC et leur affectation par rôle ;
- les corps d'état BTP, les prestations d'entretien et les services du site ;
- les plans d'abonnement avec leurs prix en FCFA (le frontend ne code aucun prix) ;
- les villes du Cameroun, les villes de la diaspora et les quartiers de Douala/Yaoundé ;
- la FAQ, les témoignages et les chiffres de confiance affichés sur la page d'accueil ;
- la configuration applicative publique (support, devise, indicateurs).

Usage :
    python manage.py seed_kemta             # socle uniquement (production)
    python manage.py seed_kemta --demo      # + jeu de démonstration complet
    python manage.py seed_kemta --demo --fresh   # recrée le jeu de démonstration
"""
from __future__ import annotations

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Permission, RolePermission
from apps.companies.models import Specialty
from apps.maintenance.models import MaintenanceServiceType
from apps.service_requests.models import ServiceCatalog
from apps.subscriptions.models import BillingInterval, Plan
from common.models import Configuration, FAQItem, Location, Testimonial, TrustStat
from common.permission_codes import ALL_PERMISSIONS, Perm

# --------------------------------------------------------------------------
# RBAC
# --------------------------------------------------------------------------
ROLE_PERMISSIONS: dict[str, list[str]] = {
    "ADMIN": list(ALL_PERMISSIONS),
    "MANAGER": [
        Perm.VIEW_PROJECT, Perm.MANAGE_PROJECT, Perm.EDIT_PROJECT, Perm.MANAGE_SCHEDULE,
        Perm.VIEW_EVIDENCE, Perm.VALIDATE_EVIDENCE, Perm.UPLOAD_EVIDENCE,
        Perm.VIEW_TASK, Perm.UPDATE_TASK, Perm.MANAGE_PHASE,
        Perm.VIEW_FINANCE, Perm.MANAGE_BUDGET, Perm.VIEW_FINANCE_REPORT,
        Perm.VIEW_REPORT, Perm.VALIDATE_REPORT, Perm.CREATE_REPORT,
        Perm.VIEW_PROPERTY, Perm.MANAGE_PROPERTY, Perm.MANAGE_MAINTENANCE, Perm.PERFORM_VISIT,
        Perm.MANAGE_SERVICE_REQUEST, Perm.VIEW_SERVICE_REQUEST, Perm.ASSIGN_SERVICE_REQUEST,
        Perm.VIEW_COMPANY, Perm.VERIFY_COMPANY, Perm.MANAGE_CATALOG,
        Perm.CREATE_OPPORTUNITY, Perm.MANAGE_OPPORTUNITY, Perm.REVIEW_APPLICATION,
        Perm.VIEW_APPLICATION, Perm.MANAGE_MEMBERS,
        Perm.VIEW_ACTIVITY, Perm.VIEW_STATISTICS, Perm.VIEW_USERS, Perm.MANAGE_NOTIFICATIONS,
    ],
    "FIELD": [
        Perm.VIEW_PROJECT, Perm.VIEW_TASK, Perm.UPDATE_TASK,
        Perm.CAPTURE_EVIDENCE, Perm.UPLOAD_EVIDENCE, Perm.VIEW_EVIDENCE,
        Perm.VIEW_PROPERTY, Perm.PERFORM_VISIT, Perm.CREATE_REPORT, Perm.VIEW_REPORT,
    ],
    "COMPANY": [
        Perm.MANAGE_COMPANY, Perm.MANAGE_CATALOG, Perm.APPLY_OPPORTUNITY,
        Perm.VIEW_APPLICATION, Perm.VIEW_SUBSCRIPTION, Perm.INITIATE_PAYMENT,
        Perm.MANAGE_MEMBERS, Perm.VIEW_TASK, Perm.UPDATE_TASK, Perm.VIEW_PROJECT,
        Perm.UPLOAD_EVIDENCE, Perm.VIEW_EVIDENCE,
    ],
    "CUSTOMER": [
        Perm.VIEW_PROJECT, Perm.VIEW_EVIDENCE, Perm.VIEW_REPORT, Perm.VIEW_PROPERTY,
        Perm.VIEW_SUBSCRIPTION, Perm.INITIATE_PAYMENT, Perm.VIEW_APPLICATION,
    ],
}

PERMISSION_CATEGORIES = {
    "PROJECT": "Chantiers",
    "EVIDENCE": "Preuves terrain",
    "TASK": "Tâches",
    "FINANCE": "Finances",
    "REPORT": "Rapports",
    "PROPERTY": "Propriétés",
    "MAINTENANCE": "Entretien",
    "SERVICE_REQUEST": "Demandes",
    "COMPANY": "Entreprises",
    "CATALOG": "Catalogue",
    "OPPORTUNITY": "Opportunités",
    "APPLICATION": "Candidatures",
    "SUBSCRIPTION": "Abonnements",
    "PAYMENT": "Paiements",
    "USERS": "Utilisateurs",
    "SETTINGS": "Paramètres",
    "ACTIVITY": "Activité",
    "AUTH_LOGS": "Sécurité",
    "NOTIFICATIONS": "Notifications",
    "STATISTICS": "Statistiques",
}

# --------------------------------------------------------------------------
# Référentiels métier
# --------------------------------------------------------------------------
SPECIALTIES = [
    ("GROS_OEUVRE", "Gros œuvre & maçonnerie", "Structure", "Murs porteurs, dalles, poteaux, fondations."),
    ("FONDATIONS", "Fondations & terrassement", "Structure", "Terrassement, semelles, longrines, radiers."),
    ("CHARPENTE", "Charpente & couverture", "Structure", "Charpentes bois/métal, tôles, tuiles."),
    ("ETANCHEITE", "Étanchéité", "Structure", "Toitures-terrasses, salles d'eau, cuvelage."),
    ("ELECTRICITE", "Électricité", "Second œuvre", "Installation, mise aux normes, tableaux, groupes."),
    ("PLOMBERIE", "Plomberie & sanitaire", "Second œuvre", "Réseaux, sanitaires, chauffe-eau, surpresseurs."),
    ("CLIMATISATION", "Climatisation & ventilation", "Second œuvre", "Split, gainable, ventilation mécanique."),
    ("CARRELAGE", "Carrelage & revêtements", "Finitions", "Sols, faïence, pierres naturelles."),
    ("PEINTURE", "Peinture & décoration", "Finitions", "Intérieure, extérieure, enduits décoratifs."),
    ("MENUISERIE_BOIS", "Menuiserie bois", "Finitions", "Portes, placards, mobilier sur mesure."),
    ("MENUISERIE_ALU", "Menuiserie aluminium & vitrerie", "Finitions", "Baies vitrées, façades, garde-corps."),
    ("METALLERIE", "Métallerie & serrurerie", "Finitions", "Portails, grilles, rampes, charpentes métal."),
    ("FORAGE", "Forage & adduction d'eau", "Technique", "Forage, château d'eau, pompes solaires."),
    ("VOIRIE", "Voirie & réseaux divers", "Technique", "Voirie, assainissement, VRD, pavage."),
    ("ASSAINISSEMENT", "Assainissement", "Technique", "Fosses septiques, puisards, réseaux EU/EP."),
    ("PISCINE", "Piscines & espaces aquatiques", "Technique", "Construction, filtration, entretien."),
    ("ESPACES_VERTS", "Espaces verts & aménagement", "Aménagement", "Pelouses, plantations, éclairage extérieur."),
    ("DEMOLITION", "Démolition & curage", "Aménagement", "Démolition contrôlée, évacuation des gravats."),
    ("ARCHITECTURE", "Architecture & études", "Études", "Plans, permis de bâtir, suivi de conformité."),
    ("TOPOGraphie", "Topographie & implantation", "Études", "Levés, implantation, bornage."),
    ("STRUCTURE_ETUDES", "Études structure & béton armé", "Études", "Notes de calcul, plans d'exécution."),
    ("SECURITE_INCENDIE", "Sécurité incendie", "Technique", "Détection, désenfumage, moyens de secours."),
]

MAINTENANCE_SERVICES = [
    ("INSPECTION", "Inspection technique complète", "VISIT", 45_000, "Contrôle complet du bâti : structure, réseaux, étanchéité, sécurité."),
    ("PLOMBERIE_URGENCE", "Plomberie & fuites", "INTERVENTION", 25_000, "Recherche et réparation de fuites, débouchage, remplacement de robinetterie."),
    ("ELECTRICITE_MAINT", "Électricité & sécurité", "INTERVENTION", 30_000, "Contrôle du tableau, prises, éclairage, mise en sécurité."),
    ("TOITURE", "Toiture & étanchéité", "INTERVENTION", 55_000, "Traitement des infiltrations, réfection de couverture et zinguerie."),
    ("HUMIDITE", "Traitement de l'humidité", "INTERVENTION", 60_000, "Diagnostic et traitement des remontées capillaires et moisissures."),
    ("PEINTURE_ENTRETIEN", "Rafraîchissement peinture", "TRAVAUX", 80_000, "Peinture intérieure et extérieure, retouches ciblées."),
    ("CLIM_MAINT", "Entretien climatisation", "INTERVENTION", 35_000, "Nettoyage, recharge de gaz, contrôle des unités."),
    ("NETTOYAGE_TECHNIQUE", "Nettoyage technique", "INTERVENTION", 40_000, "Nettoyage de façades, terrasses, citernes et locaux techniques."),
    ("DESINSECTISATION", "Désinsectisation & dératisation", "INTERVENTION", 30_000, "Traitement complet avec attestation de passage."),
    ("ESPACES_VERTS", "Entretien des espaces verts", "VISIT", 25_000, "Tonte, taille, arrosage et suivi saisonnier."),
    ("PISCINE_MAINT", "Entretien de piscine", "INTERVENTION", 45_000, "Traitement de l'eau, nettoyage, contrôle du système de filtration."),
    ("SECURITE_MAINT", "Contrôle sécurité & incendie", "VISIT", 50_000, "Vérification des extincteurs, détecteurs et issues de secours."),
]

SERVICES = [
    {
        "code": "CONSTRUIRE",
        "name": "Construire un projet",
        "tagline": "De l'idée au chantier livré, sans quitter votre téléphone.",
        "description": (
            "Nous cadrons votre projet, mobilisons les entreprises, sécurisons le budget et "
            "documentons chaque étape par des preuves terrain horodatées."
        ),
        "icon": "build",
        "order": 1,
        "duration_days": 180,
        "base_price_xaf": None,
        "requires_site_visit": True,
        "deliverables": [
            "Étude de faisabilité et estimation budgétaire",
            "Sélection d'entreprises BTP vérifiées",
            "Planning de chantier et jalons de paiement",
            "Preuves photo/vidéo à chaque étape",
        ],
    },
    {
        "code": "SUIVI_CHANTIER",
        "name": "Suivre un chantier existant",
        "tagline": "Vous avez déjà une entreprise ? Nous devenons vos yeux sur le terrain.",
        "description": (
            "Reprise de suivi en cours de chantier : contrôle de l'avancement réel, du budget "
            "engagé et de la qualité, avec un rapport clair chaque semaine."
        ),
        "icon": "monitor",
        "order": 2,
        "duration_days": 90,
        "base_price_xaf": 150_000,
        "requires_site_visit": True,
        "deliverables": [
            "Diagnostic d'avancement et de conformité",
            "Contrôle des dépenses par poste",
            "Visites hebdomadaires documentées",
            "Rapports périodiques téléchargeables",
        ],
    },
    {
        "code": "ENTRETIEN",
        "name": "Entretenir une propriété",
        "tagline": "Vos biens restent en bon état, même à distance.",
        "description": (
            "Contrat d'entretien préventif : visites planifiées, interventions d'urgence, "
            "carnet numérique de votre propriété et alertes en cas de problème."
        ),
        "icon": "maintenance",
        "order": 3,
        "duration_days": 365,
        "base_price_xaf": 90_000,
        "requires_site_visit": False,
        "deliverables": [
            "Calendrier de visites planifiées",
            "Interventions d'urgence sous 48 h",
            "Carnet d'entretien numérique",
            "Rapport photo après chaque passage",
        ],
    },
    {
        "code": "AUTRE",
        "name": "Un autre besoin",
        "tagline": "Diagnostic, évaluation, conseil : expliquez-nous.",
        "description": (
            "Diagnostic technique, évaluation de travaux, contre-expertise d'un devis, "
            "assistance pour un litige ou un projet particulier : notre équipe vous répond."
        ),
        "icon": "help",
        "order": 4,
        "duration_days": 30,
        "base_price_xaf": None,
        "requires_site_visit": False,
        "deliverables": [
            "Rappel sous 24 h ouvrées",
            "Visite technique si nécessaire",
            "Devis détaillé et transparent",
        ],
    },
]

PLANS = [
    {
        "code": "FREE",
        "name": "Découverte",
        "tagline": "Testez KEMTA sans engagement",
        "description": "Pour les entreprises qui veulent une présence sérieuse et vérifiée.",
        "price_xaf": 0,
        "interval": BillingInterval.MONTHLY,
        "trial_days": 0,
        "sort_order": 1,
        "is_recommended": False,
        "features": [
            "Profil vérifié KEMTA",
            "Jusqu'à 3 réalisations publiées",
            "2 candidatures par mois",
            "Notifications dans l'application",
        ],
        "limits": {
            "realizations": 3,
            "photos_per_realization": 6,
            "applications_per_month": 2,
            "featured": False,
            "sms_notifications": False,
            "priority_support": False,
        },
    },
    {
        "code": "PRO",
        "name": "Pro",
        "tagline": "Développez votre carnet de commandes",
        "description": "Pour les entreprises actives qui répondent régulièrement aux marchés.",
        "price_xaf": 25_000,
        "interval": BillingInterval.MONTHLY,
        "trial_days": 14,
        "sort_order": 2,
        "is_recommended": True,
        "features": [
            "20 réalisations avec photos HD",
            "15 candidatures par mois",
            "Alertes SMS sur les marchés correspondant à votre profil",
            "Statistiques de visites et d'intérêt",
            "Mise en avant dans le catalogue",
        ],
        "limits": {
            "realizations": 20,
            "photos_per_realization": 20,
            "applications_per_month": 15,
            "featured": True,
            "sms_notifications": True,
            "priority_support": False,
        },
    },
    {
        "code": "PREMIUM",
        "name": "Premium",
        "tagline": "Positionnez-vous en tête sur votre métier",
        "description": "Pour les entreprises de référence qui doivent être trouvées en premier.",
        "price_xaf": 75_000,
        "interval": BillingInterval.MONTHLY,
        "trial_days": 14,
        "sort_order": 3,
        "is_recommended": False,
        "features": [
            "Réalisations illimitées",
            "Candidatures illimitées",
            "Position prioritaire sur votre ville et votre corps d'état",
            "Accompagnement dédié KEMTA",
            "Rapport mensuel de performance commerciale",
        ],
        "limits": {
            "realizations": None,
            "photos_per_realization": 40,
            "applications_per_month": None,
            "featured": True,
            "sms_notifications": True,
            "priority_support": True,
        },
    },
]

CITIES = [
    ("Douala", "LITTORAL", True), ("Yaoundé", "CENTRE", True), ("Bafoussam", "OUEST", True),
    ("Bamenda", "NORD-OUEST", False), ("Garoua", "NORD", False), ("Maroua", "EXTRÊME-NORD", False),
    ("Ngaoundéré", "ADAMAOUA", False), ("Kribi", "SUD", True), ("Limbe", "SUD-OUEST", False),
    ("Buea", "SUD-OUEST", True), ("Ebolowa", "SUD", False), ("Dschang", "OUEST", False),
    ("Edéa", "LITTORAL", False), ("Kumba", "SUD-OUEST", False), ("Bertoua", "EST", False),
    ("Nkongsamba", "LITTORAL", False), ("Foumban", "OUEST", False), ("Bafia", "CENTRE", False),
    ("Mbalmayo", "CENTRE", False), ("Tiko", "SUD-OUEST", False),
]

DIASPORA_CITIES = [
    ("Paris", "FR", "Île-de-France"), ("Bruxelles", "BE", "Bruxelles-Capitale"),
    ("Montréal", "CA", "Québec"), ("Washington", "US", "District of Columbia"),
    ("Dubaï", "AE", "Dubaï"), ("Johannesburg", "ZA", "Gauteng"),
    ("Libreville", "GA", "Estuaire"), ("Malabo", "GQ", "Bioko"),
    ("Milan", "IT", "Lombardie"), ("Francfort", "DE", "Hesse"),
]

NEIGHBOURHOODS = [
    ("Bonapriso", "Douala"), ("Bonanjo", "Douala"), ("Akwa", "Douala"),
    ("Bonabéri", "Douala"), ("Makepe", "Douala"), ("Logbessou", "Douala"),
    ("Ndokoti", "Douala"), ("Bepanda", "Douala"), ("Cité des Palmiers", "Douala"),
    ("Kotto", "Douala"), ("Bali", "Douala"), ("Yassa", "Douala"),
    ("Bastos", "Yaoundé"), ("Odza", "Yaoundé"), ("Mvan", "Yaoundé"),
    ("Nsam", "Yaoundé"), ("Biyem-Assi", "Yaoundé"), ("Mimboman", "Yaoundé"),
    ("Ngoa-Ekelle", "Yaoundé"), ("Ekounou", "Yaoundé"), ("Etoudi", "Yaoundé"),
]

FAQ = [
    (
        "Comment KEMTA me permet-il de suivre mon chantier depuis l'étranger ?",
        "Chaque intervention de terrain est documentée : photos horodatées, vidéos, rapports "
        "d'avancement et notes du chargé de suivi. Vous consultez tout depuis votre téléphone, où "
        "que vous soyez, et vous recevez une alerte à chaque étape validée.",
        "Suivi",
    ),
    (
        "Qui sont les entreprises BTP présentes sur la plateforme ?",
        "Elles sont toutes enregistrées au registre du commerce. KEMTA contrôle leurs pièces "
        "administratives et leurs références de chantier avant d'attribuer le badge « Vérifiée », "
        "affiché sur leur profil public.",
        "Entreprises",
    ),
    (
        "Comment l'argent de mon chantier est-il protégé ?",
        "Le budget est découpé par postes et par jalons. Vous ne payez la suite qu'après validation "
        "de l'étape précédente, preuves à l'appui. Chaque paiement est tracé et vous recevez une "
        "facture KEMTA.",
        "Paiement & confiance",
    ),
    (
        "Quel est le prix des services KEMTA ?",
        "Le suivi de chantier démarre à 150 000 FCFA et l'entretien de propriété à 90 000 FCFA par an. "
        "Pour la construction, la prestation KEMTA est calculée selon la surface et la complexité, "
        "et vous recevez un devis détaillé avant tout engagement.",
        "Paiement & confiance",
    ),
    (
        "Puis-je faire appel à mon propre entrepreneur ?",
        "Oui. KEMTA peut suivre le chantier mené par l'entreprise de votre choix : contrôle de "
        "l'avancement, du budget et de la qualité, avec des preuves destinées à votre assureur ou "
        "à votre banque si besoin.",
        "Services",
    ),
    (
        "Que se passe-t-il en cas de malfaçon ou de retard ?",
        "Le chargé de suivi documente l'écart dans le rapport de visite et l'entreprise dispose d'un "
        "délai de correction. Si le problème persiste, KEMTA peut suspendre les décaissements et "
        "médier pour vous.",
        "Services",
    ),
    (
        "Comment fonctionnent les visites d'entretien ?",
        "Vous choisissez une fréquence (mensuelle à annuelle). Les visites sont planifiées à "
        "l'avance, le technicien photographie chaque point de contrôle et vous recevez un compte "
        "rendu, même si aucun problème n'a été détecté.",
        "Entretien",
    ),
    (
        "Mes numéros de téléphone et mes documents sont-ils protégés ?",
        "Vos données sont chiffrées et hébergées de manière sûre. Les échanges sensibles passent "
        "par notre API authentifiée et les documents ne sont jamais exposés publiquement. "
        "Vous gardez la maîtrise de vos informations.",
        "Confidentialité",
    ),
]

TESTIMONIALS = [
    (
        "Je suis mon chantier depuis Montréal, chaque vendredi j'ai mes photos et mon rapport. "
        "J'ai récupéré 4 mois de retard sur une entreprise qui traînait.",
        "Jules Etaba", "Diaspora · Montréal", "Propriétaire bailleur", 5,
    ),
    (
        "Le découpage du budget par étapes m'a évité de payer des travaux non faits. "
        "Le suivi de KEMTA a changé ma façon de construire.",
        "Mireille Ngono", "Douala, Bonapriso", "Cliente construction", 5,
    ),
    (
        "Nos interventions sont documentées et le client reçoit tout immédiatement. "
        "Ça a réduit nos litiges et nous a apporté 6 nouveaux chantiers en un an.",
        "Achille Fotso", "Douala, Akwa", "Directeur — BTP Sawa Construction", 5,
    ),
    (
        "L'entretien préventif de mes 3 immeubles ne me coûte plus rien en surprises : "
        "je vois ce qui est fait, quand, et avec les photos.",
        "Sandrine Mbappe", "Yaoundé, Bastos", "Propriétaire d'immeubles", 5,
    ),
    (
        "J'ai trouvé une entreprise vérifiée en deux jours et candidaté à un marché "
        "sur la même plateforme. Simple et sérieux.",
        "Ibrahim Kouam", "Bafoussam", "Gérant d'entreprise BTP", 4,
    ),
    (
        "Le rapport de visite a servi de preuve face à mon ancien entrepreneur. "
        "KEMTA a suspendu les paiements et tout a été corrigé.",
        "Prosper Ekane", "Kribi", "Investisseur immobilier", 5,
    ),
]

TRUST_STATS = [
    ("Chantiers suivis", "180+", "Depuis 2021, du gros œuvre à la livraison.", "building"),
    ("Entreprises vérifiées", "75", "Chaque dossier contrôlé pièce par pièce.", "shield"),
    ("Preuves terrain publiées", "12 400", "Photos horodatées et géolocalisées.", "camera"),
    ("Villes couvertes", "20", "Cameroun, plus l'accompagnement diaspora.", "map"),
    ("Délai moyen de réponse", "24 h", "Un chargé de suivi dédié à votre dossier.", "clock"),
    ("Satisfaction clients", "4,8/5", "Sur les 96 derniers avis publiés.", "star"),
]

CONFIGURATION = [
    ("support_phone", "+237 6 99 00 00 00", "Contact téléphonique KEMTA", True),
    ("support_email", "contact@kemta.cm", "Adresse e-mail du support", True),
    ("whatsapp_number", "+237 6 99 00 00 00", "Numéro WhatsApp Business", True),
    ("support_hours", "Lun–Ven 7h30–18h, Sam 8h–13h", "Horaires du support", True),
    ("head_office", "Bonanjo, Douala — Cameroun", "Adresse du siège", True),
    ("currency", "XAF", "Devise d'affichage", True),
    ("min_payment_xaf", 5000, "Montant minimum d'un paiement en ligne", True),
]


class Command(BaseCommand):
    help = "Installe les données de référence KEMTA (plans, référentiels, contenus, RBAC)."

    def add_arguments(self, parser):
        parser.add_argument("--demo", action="store_true", help="Ajoute un jeu de démonstration complet.")
        parser.add_argument("--fresh", action="store_true", help="Supprime d'abord le jeu de démonstration.")

    @transaction.atomic
    def handle(self, *args, **options):
        self._seed_permissions()
        self._seed_specialties()
        self._seed_maintenance_services()
        self._seed_services()
        self._seed_plans()
        self._seed_locations()
        self._seed_content()
        self._seed_configuration()
        if options["demo"]:
            if options["fresh"]:
                self._purge_demo()
            self._seed_demo()
        self.stdout.write(self.style.SUCCESS("Données de référence KEMTA installées."))

    # -- RBAC --------------------------------------------------------------
    def _seed_permissions(self) -> None:
        created = 0
        permissions: dict[str, Permission] = {}
        for code, label in ALL_PERMISSIONS.items():
            category = PERMISSION_CATEGORIES.get(code.split("_")[0], "Général")
            if code.startswith(("MANAGE_", "VIEW_")) and code.split("_", 1)[1] in PERMISSION_CATEGORIES:
                category = PERMISSION_CATEGORIES[code.split("_", 1)[1]]
            permission, was_created = Permission.objects.update_or_create(
                code=code,
                defaults={
                    "label": label,
                    "category": category,
                    "description": f"Autorise l'action « {label.lower()} ».",
                },
            )
            permissions[code] = permission
            created += int(was_created)

        links = 0
        for role, codes in ROLE_PERMISSIONS.items():
            for code in codes:
                permission = permissions.get(code)
                if permission is None:
                    continue
                _, was_created = RolePermission.objects.get_or_create(
                    role=role, permission=permission, defaults={"allowed": True}
                )
                links += int(was_created)
        self.stdout.write(f"  · RBAC : {len(permissions)} permissions, {links} affectations créées")

    # -- Référentiels ------------------------------------------------------
    def _seed_specialties(self) -> None:
        for order, (code, name, category, description) in enumerate(SPECIALTIES, start=1):
            Specialty.objects.update_or_create(
                code=code,
                defaults={
                    "name": name, "category": category, "description": description,
                    "order": order, "is_active": True,
                },
            )
        self.stdout.write(f"  · {len(SPECIALTIES)} corps d'état BTP")

    def _seed_maintenance_services(self) -> None:
        for order, (code, name, unit, price, description) in enumerate(MAINTENANCE_SERVICES, start=1):
            MaintenanceServiceType.objects.update_or_create(
                code=code,
                defaults={
                    "name": name, "unit": unit, "base_price_xaf": Decimal(price),
                    "description": description, "order": order, "is_active": True,
                    "requires_technician": True,
                },
            )
        self.stdout.write(f"  · {len(MAINTENANCE_SERVICES)} prestations d'entretien")

    def _seed_services(self) -> None:
        for item in SERVICES:
            ServiceCatalog.objects.update_or_create(
                code=item["code"],
                defaults={
                    "name": item["name"], "tagline": item["tagline"], "description": item["description"],
                    "icon": item["icon"], "order": item["order"], "duration_days": item["duration_days"],
                    "base_price_xaf": (
                        Decimal(item["base_price_xaf"]) if item["base_price_xaf"] is not None else None
                    ),
                    "requires_site_visit": item["requires_site_visit"],
                    "deliverables": item["deliverables"],
                    "is_active": True,
                },
            )
        self.stdout.write(f"  · {len(SERVICES)} services du site public")

    def _seed_plans(self) -> None:
        from django.core.cache import cache

        for item in PLANS:
            plan, created = Plan.objects.update_or_create(
                code=item["code"],
                defaults={
                    "name": item["name"], "tagline": item["tagline"], "description": item["description"],
                    "price_xaf": Decimal(item["price_xaf"]), "currency": "XAF",
                    "interval": item["interval"], "trial_days": item["trial_days"],
                    "features": item["features"], "limits": item["limits"],
                    "sort_order": item["sort_order"], "is_recommended": item["is_recommended"],
                    "is_public": True, "is_active": True,
                },
            )
            if created:
                self.stdout.write(f"    – plan {plan.name} créé ({plan.price_label})")
        cache.delete_pattern("kemta:*") if hasattr(cache, "delete_pattern") else None
        self.stdout.write(f"  · {len(PLANS)} plans d'abonnement")

    def _seed_locations(self) -> None:
        from common.utils import slugify

        for name, region, is_major in CITIES:
            Location.objects.update_or_create(
                country="CM", name=name, kind="CITY",
                defaults={
                    "slug": slugify(f"{name}-cm"), "region": region, "is_active": True,
                    "latitude": None, "longitude": None,
                },
            )
            if is_major:
                for hood in [h for h, city in NEIGHBOURHOODS if city == name]:
                    Location.objects.update_or_create(
                        country="CM", name=hood, kind="NEIGHBOURHOOD",
                        defaults={"slug": slugify(f"{hood}-{name}"), "region": region, "is_active": True},
                    )
        for name, country, region in DIASPORA_CITIES:
            Location.objects.update_or_create(
                country=country, name=name, kind="DIASPORA_CITY",
                defaults={"slug": slugify(f"{name}-{country.lower()}"), "region": region, "is_active": True},
            )
        self.stdout.write(
            f"  · {len(CITIES)} villes du Cameroun, {len(NEIGHBOURHOODS)} quartiers, "
            f"{len(DIASPORA_CITIES)} villes de la diaspora"
        )

    def _seed_content(self) -> None:
        for order, (question, answer, category) in enumerate(FAQ, start=1):
            FAQItem.objects.update_or_create(
                question=question,
                defaults={"answer": answer, "category": category, "order": order, "is_active": True},
            )
        for order, (quote, author, role, city, rating) in enumerate(TESTIMONIALS, start=1):
            Testimonial.objects.update_or_create(
                author_name=author,
                defaults={
                    "quote": quote, "rating": rating, "order": order, "is_published": True,
                    "author_role": role, "author_city": city, "author_country": "CM",
                },
            )
        for order, (label, value, hint, icon) in enumerate(TRUST_STATS, start=1):
            TrustStat.objects.update_or_create(
                label=label,
                defaults={"value": value, "hint": hint, "icon": icon, "order": order, "is_active": True},
            )
        self.stdout.write(f"  · {len(FAQ)} questions, {len(TESTIMONIALS)} témoignages, {len(TRUST_STATS)} chiffres")

    def _seed_configuration(self) -> None:
        for key, value, label, is_public in CONFIGURATION:
            Configuration.objects.update_or_create(
                key=key, defaults={"value": value, "label": label, "is_public": is_public}
            )
        self.stdout.write(f"  · {len(CONFIGURATION)} paramètres publics")

    # -- Jeu de démonstration ---------------------------------------------
    def _purge_demo(self) -> None:
        from django.contrib.auth import get_user_model

        User = get_user_model()
        demo_users = User.objects.filter(phone__startswith="+237600")
        count = demo_users.count()
        if count:
            demo_users.filter(role__in=["CUSTOMER", "COMPANY"]).delete()
            self.stdout.write(f"  · jeu de démonstration précédent supprimé ({count} comptes)")

    def _seed_demo(self) -> None:
        from scripts.seed_demo import seed_demo_data

        summary = seed_demo_data(stdout=self.stdout)
        self.stdout.write(f"  · démonstration : {summary}")
