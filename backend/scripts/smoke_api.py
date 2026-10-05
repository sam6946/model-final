#!/usr/bin/env python
"""Vérification de bout en bout de l'API KEMTA (développement / CI).

Ce script n'est pas un test unitaire : il ouvre de vraies sessions HTTP contre un
serveur en cours d'exécution et parcourt les parcours critiques du produit, dans
l'ordre où un utilisateur les vit :

1. inscription d'un client par SMS OTP (téléphone d'abord, e-mail facultatif) ;
2. profil, permissions RBAC et tableau de bord agrégé ;
3. demande de service publique (formulaire multi-étapes) ;
4. qualification puis conversion de la demande en projet par KEMTA ;
5. suivi du projet côté client (phases, preuves, rapports) ;
6. propriété + contrat d'entretien + visite réalisée ;
7. compte entreprise, dossier vérifié, réalisation publiée ;
8. marché publié par KEMTA puis candidature de l'entreprise ;
9. abonnement, facture et encaissement idempotent ;
10. tableaux de bord client / entreprise / back-office.

Usage :
    python scripts/smoke_api.py                      # serveur sur :8000
    KEMTA_BASE_URL=http://127.0.0.1:8001 python scripts/smoke_api.py

Le script crée ses propres comptes (préfixe +237600) et n'échoue jamais
silencieusement : chaque étape est journalisée, et le code de sortie vaut 1 si
une seule étape échoue.
"""
from __future__ import annotations

import os
import random
import sys
import time

import requests

BASE = os.environ.get("KEMTA_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
API = f"{BASE}/api/v1"
PASSWORD = "Kemta!2026demo"

PASSED: list[str] = []
FAILED: list[tuple[str, str]] = []


class StepFailure(Exception):
    pass


def unique_phone() -> str:
    """Numéro camerounais plausible, unique à chaque exécution."""
    return "+2376" + "".join(str(random.randint(0, 9)) for _ in range(8))


def call(method: str, path: str, token: str | None = None, expect=(200, 201), **payload):
    url = path if path.startswith("http") else f"{API}{path}"
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = requests.request(method, url, headers=headers, json=payload or None, timeout=40)
    if response.status_code not in expect:
        raise StepFailure(
            f"{method} {path} → {response.status_code} (attendu {expect})\n"
            f"        {response.text[:700]}"
        )
    if not response.content:
        return {}
    try:
        return response.json()
    except ValueError:
        return {"raw": response.text[:400]}


def upload_image(token: str, *, upload_kind: str, filename: str) -> dict:
    """Envoie une image réelle (PNG généré) via l'endpoint d'envoi direct."""
    from io import BytesIO

    from PIL import Image

    buffer = BytesIO()
    Image.new("RGB", (600, 400), (6, 59, 92)).save(buffer, format="PNG")
    buffer.seek(0)
    response = requests.post(
        f"{API}/uploads/direct/",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        data={"upload_kind": upload_kind},
        files={"file": (filename, buffer.getvalue(), "image/png")},
        timeout=60,
    )
    if response.status_code not in (200, 201):
        raise StepFailure(f"POST /uploads/direct/ → {response.status_code}\n        {response.text[:400]}")
    return response.json()


def step(label: str):
    def wrapper(func):
        def runner(*args, **kwargs):
            started = time.time()
            try:
                result = func(*args, **kwargs)
            except StepFailure as exc:
                FAILED.append((label, str(exc)))
                print(f"  ✗ {label}\n        {exc}")
                return None
            except Exception as exc:  # noqa: BLE001 - le script rapporte tout
                FAILED.append((label, f"{type(exc).__name__}: {exc}"))
                print(f"  ✗ {label}\n        {type(exc).__name__}: {exc}")
                return None
            print(f"  ✓ {label} ({int((time.time() - started) * 1000)} ms)")
            PASSED.append(label)
            return result

        return runner

    return wrapper


def register_account(*, first: str, last: str, city: str = "Douala") -> dict:
    """Inscription complète : OTP → ticket → compte → jetons."""
    numero = unique_phone()
    otp = call("POST", "/auth/otp/request/", phone=numero, purpose="REGISTER")
    code = otp.get("dev_code")
    if not code:
        raise StepFailure(
            "Aucun code de développement renvoyé : vérifiez DEBUG=True et OTP_DEV_ECHO=True "
            "dans config/settings/dev.py."
        )
    verified = call("POST", "/auth/otp/verify/", phone=numero, purpose="REGISTER", code=code)
    ticket = verified.get("verification_ticket")
    if not ticket:
        raise StepFailure(f"Ticket de vérification absent : {verified}")
    account = call(
        "POST", "/auth/register/",
        phone=numero, verification_ticket=ticket,
        password=PASSWORD, password_confirm=PASSWORD,
        first_name=first, last_name=last, city=city, country="CM", terms_accepted=True,
    )
    if not account.get("access"):
        raise StepFailure(f"Inscription sans jeton d'accès : {account}")
    return {"phone": numero, "token": account["access"], "refresh": account["refresh"]}


def ensure_admin() -> dict:
    """Crée (si besoin) le gestionnaire KEMTA de test et ouvre sa session."""
    import django

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, root)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
    django.setup()
    from django.contrib.auth import get_user_model

    User = get_user_model()
    numero = "+237600000001"
    user, _created = User.objects.get_or_create(
        phone=numero,
        defaults={
            "first_name": "Serge", "last_name": "Nkoulou", "role": "ADMIN",
            "is_staff": True, "is_superuser": True, "phone_verified": True, "city": "Douala",
        },
    )
    user.role = "ADMIN"
    user.is_staff = True
    user.is_superuser = True
    user.phone_verified = True
    user.set_password(PASSWORD)
    user.save()
    session = call("POST", "/auth/login/", phone=numero, password=PASSWORD)
    return {"phone": numero, "token": session["access"], "refresh": session["refresh"]}


def main() -> int:
    print(f"\nKEMTA — vérification de bout en bout sur {BASE}\n")

    # ------------------------------------------------------------------ admin
    print("Back-office KEMTA")
    admin = ensure_admin()
    admin_me = call("GET", "/auth/me/", token=admin["token"])
    admin["user_id"] = admin_me["user"]["id"]

    @step("Connexion du gestionnaire KEMTA (rôle ADMIN)")
    def _admin_ok():
        data = call("GET", "/auth/me/", token=admin["token"])
        if data["user"]["role"] != "ADMIN":
            raise StepFailure(f"Rôle inattendu : {data['user']['role']}")
        return data

    @step("Permissions RBAC du gestionnaire")
    def _admin_permissions():
        data = call("GET", "/auth/permissions/", token=admin["token"])
        codes = data.get("permissions") or data.get("codes") or []
        if "MANAGE_PROJECT" not in codes:
            raise StepFailure(f"MANAGE_PROJECT absent des permissions : {codes[:8]}")
        return data

    _admin_ok()
    _admin_permissions()

    # ---------------------------------------------------------------- client
    print("\nParcours client (téléphone → projet suivi)")
    client = register_account(first="Aïcha", last="Mbarga")

    @step("Profil connecté (GET /auth/me/)")
    def _me():
        data = call("GET", "/auth/me/", token=client["token"])
        if data["user"]["phone"] != client["phone"]:
            raise StepFailure("Le numéro du profil ne correspond pas à celui inscrit.")
        if not data.get("phone_verified"):
            raise StepFailure("Le téléphone devrait être marqué comme vérifié.")
        return data

    @step("Tableau de bord client (un seul appel)")
    def _dashboard():
        data = call("GET", "/dashboard/", token=client["token"])
        for key in ("user", "statistics", "projects", "notifications", "next_actions"):
            if key not in data:
                raise StepFailure(f"Clé manquante : {key}")
        return data

    @step("Demande de service publique (formulaire multi-étapes)")
    def _service_request():
        data = call(
            "POST", "/requests/", token=client["token"],
            kind="BUILD_PROJECT",
            first_name="Aïcha", last_name="Mbarga",
            phone=client["phone"], email="aicha.mbarga@example.cm",
            city="Douala", location_text="Bonapriso, Douala", country="CM",
            project_type="VILLA", property_type="VILLA",
            budget_min_xaf="25000000", budget_max_xaf="42000000",
            desired_start_date="2026-12-01", description=(
                "Construction d'une villa 4 chambres avec dépendance sur un terrain "
                "clôturé de 500 m² à Bonapriso."
            ),
            has_land=True, has_plans=False, terms_accepted=True,
            requirements=["plan_3d", "suivi_chantier"],
        )
        if not str(data.get("reference", "")).startswith("KEMTA-REQ-"):
            raise StepFailure(f"Référence inattendue : {data.get('reference')}")
        return data

    request_data = _service_request()
    request_reference = (request_data or {}).get("reference")

    @step("Retrouver la demande côté back-office (par référence)")
    def _find_request():
        if not request_reference:
            raise StepFailure("Référence de demande indisponible.")
        listing = call("GET", f"/admin/requests/?search={request_reference}", token=admin["token"])
        rows = listing.get("results") or []
        if not rows:
            raise StepFailure("La demande n'apparaît pas dans le back-office.")
        return rows[0]

    request_row = _find_request()
    request_id = (request_row or {}).get("id")

    @step("Qualification de la demande par KEMTA")
    def _qualify():
        if not request_id:
            raise StepFailure("Demande indisponible (étape précédente en échec).")
        return call(
            "POST", f"/admin/requests/{request_id}/status/",
            token=admin["token"], status="QUALIFIED", comment="Dossier complet, visite à programmer.",
        )

    @step("Conversion de la demande en projet suivi")
    def _convert():
        if not request_id:
            raise StepFailure("Demande indisponible.")
        data = call(
            "POST", f"/admin/requests/{request_id}/convert/", token=admin["token"],
            name="Villa Bonapriso — Aïcha Mbarga", kind="BUILD",
            budget_total_xaf=38_000_000, manager=admin.get("user_id"),

        )
        if not data.get("project_reference"):
            raise StepFailure(f"Projet non créé : {data}")
        return data

    project = _convert()

    @step("Le client voit son projet, ses phases et son budget")
    def _project_visible():
        if not project:
            raise StepFailure("Projet indisponible.")
        listing = call("GET", "/projects/mine/", token=client["token"])
        rows = listing.get("results", [])
        if not any(row["reference"] == project["project_reference"] for row in rows):
            raise StepFailure("Le projet converti n'apparaît pas dans l'espace client.")
        if "summary" not in listing:
            raise StepFailure("Le résumé de portefeuille est absent de la liste.")
        detail = call("GET", f"/projects/{project['project_id']}/", token=client["token"])
        for key in ("reference", "metrics", "physical_progress", "budget_total_xaf"):
            if key not in detail:
                raise StepFailure(f"Clé absente du détail projet : {key}")
        phases = call("GET", f"/projects/{project['project_id']}/phases/", token=client["token"])
        rows = phases.get("results") if isinstance(phases, dict) else phases
        if not rows:
            raise StepFailure("Aucune phase générée pour le projet.")
        timeline = call("GET", f"/projects/{project['project_id']}/timeline/", token=client["token"])
        if not (timeline.get("events") or timeline.get("results")):
            raise StepFailure("Journal du projet vide : le client ne peut pas suivre le chantier.")
        return detail

    @step("Preuve terrain publiée par un technicien KEMTA")
    def _evidence():
        if not project:
            raise StepFailure("Projet indisponible.")
        asset = upload_image(admin["token"], upload_kind="EVIDENCE_PHOTO", filename="fondations.png")
        created = call(
            "POST", f"/projects/{project['project_id']}/evidences/", token=admin["token"],
            kind="PHOTO", title="Fondations coulées",
            caption="Semelles et longrines coulées, contrôle des niveaux effectué.",
            asset=asset["id"], is_visible_to_customer=True,
        )
        evidence = created.get("evidence") or created
        call(
            "POST", f"/projects/{project['project_id']}/evidences/{evidence['id']}/review/",
            token=admin["token"], action="validate", comment="Preuve conforme, publiée au client.",
        )
        return evidence

    @step("Ajout d'une propriété (espace client)")
    def _property():
        prop = call(
            "POST", "/properties/", token=client["token"],
            name="Résidence Akwa — 3 appartements",
            property_type="IMMEUBLE", occupancy_status="RENTED",
            city="Douala", location_text="Akwa, Douala", country="CM",
            rooms_count=6, bathrooms_count=3, area_m2=240, levels_count=3,
            year_built=2018, estimated_value_xaf=180_000_000,
            monthly_rent_xaf=450_000, tenant_name="Locataire en place",
            documentation_status="COMPLETE", title_deed_number="TF-1234/DLA",
            has_water=True, has_electricity=True, is_fenced=True,
        )
        if not prop.get("id"):
            raise StepFailure(f"Propriété non créée : {prop}")
        return prop

    prop = _property()

    @step("Contrat d'entretien trimestriel")
    def _contract():
        if not prop:
            raise StepFailure("Propriété indisponible.")
        services = call("GET", "/maintenance/services/", token=admin["token"])
        rows = services.get("results") or []
        if not rows:
            raise StepFailure("Catalogue d'entretien vide : lancez `manage.py seed_kemta`.")
        contract = call(
            "POST", "/maintenance/contracts/", token=admin["token"],
            property=prop["id"], frequency="QUARTERLY",
            service_ids=[row["id"] for row in rows[:3]],
            start_date="2026-10-15", visits_included=4,
            instructions="Entretien préventif trimestriel, carnet numérique KEMTA.",
        )
        if not contract.get("id"):
            raise StepFailure(f"Contrat non créé : {contract}")
        return contract

    @step("Visite d'entretien générée puis clôturée")
    def _visit():
        visits = call("GET", "/maintenance/visits/?status=SCHEDULED", token=admin["token"])
        rows = visits.get("results") or []
        if not rows:
            raise StepFailure("Aucune visite planifiée : la génération automatique a échoué.")
        visit_id = rows[0]["id"]
        return call(
            "POST", f"/maintenance/visits/{visit_id}/complete/", token=admin["token"],
            report="Visite réalisée : réseaux, étanchéité et menuiseries contrôlés, aucun défaut majeur.",
            score=84,
        )

    _me()
    _dashboard()
    _qualify()
    _project_visible()
    _evidence()
    _contract()
    _visit()

    # ------------------------------------------------------------- entreprise
    print("\nParcours entreprise BTP (dossier → réalisations → marché)")
    company_account = register_account(first="Achille", last="Fotso")

    @step("Création du profil entreprise")
    def _company():
        specialties = call("GET", "/catalog/specialties/")
        rows = specialties.get("results") or []
        if not rows:
            raise StepFailure("Aucun corps d'état : lancez `manage.py seed_kemta`.")
        data = call(
            "POST", "/company/mine/", token=company_account["token"],
            name="BTP Sawa Construction SARL",
            description=(
                "Entreprise générale de bâtiment basée à Douala depuis 2012 : gros œuvre, "
                "second œuvre et finitions pour villas, immeubles et locaux professionnels."
            ),
            legal_name="BTP SAWA CONSTRUCTION SARL",
            registration_number="RC/DLA/2012/B/1234", tax_number="M021234567890A",
            city="Douala", region="LT", address="Rue Njo-Njo, Bonanjo",
            phone=company_account["phone"], email="contact@btp-sawa.cm",
            years_experience=12, employees_count=34, projects_count=58,
            specialties=[row["id"] for row in rows[:4]],
            intervention_regions=["LITTORAL", "CENTRE", "OUEST"],
            equipment_summary="Bétonnières, échafaudages, camion benne, outillage électroportatif.",
        )
        company = data.get("company") or {}
        if not company.get("slug"):
            raise StepFailure(f"Profil entreprise non créé : {data}")
        return company

    @step("Logo et photo de couverture de l'entreprise")
    def _brand_assets():
        logo = upload_image(company_account["token"], upload_kind="COMPANY_LOGO", filename="logo-btp-sawa.png")
        cover = upload_image(company_account["token"], upload_kind="COMPANY_COVER", filename="chantier-btp-sawa.png")
        updated = call(
            "PATCH", "/company/mine/", token=company_account["token"],
            logo=logo["id"], cover=cover["id"],
        )
        company = updated.get("company") or updated
        if not company.get("logo_url") and not company.get("logo"):
            raise StepFailure("Le logo n'a pas été enregistré sur le profil.")
        return company

    @step("Dépôt et validation du dossier administratif (RCCM + attestation fiscale)")
    def _documents():
        pieces = [
            ("REGISTRE_COMMERCE", "Registre de commerce et du crédit mobilier", "RC/DLA/2012/B/1234"),
            ("ATTESTATION_FISCALE", "Attestation de non-redevance fiscale", "DGI-2026-778211"),
        ]
        reviewed_documents = []
        for kind, title, reference in pieces:
            asset = upload_image(
                company_account["token"], upload_kind="DOCUMENT", filename=f"{kind.lower()}.png"
            )
            document = call(
                "POST", "/company/documents/", token=company_account["token"],
                kind=kind, title=title, asset=asset["id"], reference_number=reference,
            )
            reviewed = call(
                "POST", f"/company/documents/{document['id']}/review/", token=admin["token"],
                status="APPROVED", notes="Pièce conforme, référence vérifiée.",
            )
            if reviewed.get("status") != "APPROVED":
                raise StepFailure(f"Pièce non validée : {reviewed.get('status')}")
            reviewed_documents.append(reviewed)
        return reviewed_documents

    @step("Décision de vérification KEMTA (dossier complet exigé)")
    def _verification():
        if not company_profile:
            raise StepFailure("Profil entreprise indisponible.")
        try:
            return call(
                "POST", f"/admin/companies/{company_profile['id']}/verify/", token=admin["token"],
                approve=True, notes="Pièces conformes, références vérifiées sur chantier.",
            )
        except StepFailure as exc:
            # Un dossier incomplet doit être refusé par le serveur : c'est le comportement attendu.
            if "incomplete_profile" in str(exc):
                raise StepFailure(
                    "Le serveur exige un dossier complet : ajoutez des documents validés avant la vérification."
                ) from None
            raise

    @step("Réalisation publiée dans le catalogue")
    def _realization():
        specialties = call("GET", "/catalog/specialties/")["results"]
        data = call(
            "POST", "/company/realizations/", token=company_account["token"],
            title="Villa R+1 de 320 m² — Bonapriso",
            realization_type="VILLA",
            description=(
                "Construction complète d'une villa R+1 de 320 m² habitables, livrée en 11 mois "
                "avec suivi hebdomadaire et contrôle budgétaire KEMTA."
            ),
            location_text="Bonapriso, Douala", country="CM", year=2025,
            surface_m2=320, levels_count=2, rooms_count=5, duration_days=330,
            budget_xaf=95_000_000, budget_visible=False,
            services=[specialties[0]["id"], specialties[1]["id"]],
        )
        realization = data.get("realization") or {}
        if not realization.get("id"):
            raise StepFailure(f"Réalisation non créée : {data}")
        return realization

    @step("Marché publié par KEMTA (opportunité publique)")
    def _opportunity():
        data = call(
            "POST", "/admin/opportunities/", token=admin["token"],
            title="Construction d'un immeuble R+3 à Douala — 12 logements",
            description=(
                "Marché privé pour un immeuble R+3 de 12 logements sur un terrain de 600 m² à "
                "Makepe, Douala. Étude de sol et plans architecturaux disponibles."
            ),
            property_type="IMMEUBLE", location_text="Makepe, Douala", country="CM",
            budget_min_xaf=320_000_000, budget_max_xaf=420_000_000, budget_visible=True,
            start_date="2027-01-15", duration_days=540, application_deadline="2026-12-20",
            minimum_experience_years=5, requires_verified_company=True,
            status="OPEN", visibility="PUBLIC", is_featured=True,
            site_available_for_visit=True,
        )
        if not data.get("slug"):
            raise StepFailure(f"Marché non créé : {data}")
        call("POST", f"/admin/opportunities/{data['id']}/publish/", token=admin["token"])
        return data

    opportunity = _opportunity()

    @step("Marché visible publiquement puis candidature de l'entreprise")
    def _apply():
        if not opportunity:
            raise StepFailure("Marché indisponible.")
        public = call("GET", "/opportunities/")
        if not any(row["slug"] == opportunity["slug"] for row in public.get("results", [])):
            raise StepFailure("Le marché publié n'apparaît pas dans la liste publique.")
        created = call(
            "POST", f"/opportunities/{opportunity['slug']}/apply/", token=company_account["token"],
            presentation=(
                "BTP Sawa Construction SARL, 12 ans d'expérience et 58 chantiers livrés à Douala "
                "et Yaoundé. Équipe de 34 personnes dont 4 conducteurs de travaux, matériel en "
                "propre, capacité à démarrer sous 30 jours avec un suivi hebdomadaire documenté."
            ),
            similar_experience="Villa R+1 Bonapriso (320 m²), immeuble R+2 Bonabéri (8 logements).",
            methodology=(
                "Implantation et fondations, structure en béton armé coulée en place, second œuvre "
                "en parallèle des finitions par niveau, réception par étape."
            ),
            estimated_budget_xaf=378_000_000, proposed_duration_days=520, team_size=34,
            team_composition="4 conducteurs, 6 chefs d'équipe, 24 ouvriers qualifiés",
            accepts_site_visit=True,
        )
        if not str(created.get("reference", "")).startswith("KEMTA-CAN-"):
            raise StepFailure(f"Référence de candidature inattendue : {created.get('reference')}")
        return created

    @step("Instruction de la candidature (présélection)")
    def _review():
        applications = call("GET", "/admin/applications/?pending=1", token=admin["token"])
        rows = applications.get("results") or []
        if not rows:
            raise StepFailure("Aucune candidature à instruire.")
        data = call(
            "PATCH", f"/admin/applications/{rows[0]['id']}/", token=admin["token"],
            status="SHORTLISTED", score="82",
            internal_notes="Références vérifiées, capacité financière à confirmer.",
            client_feedback="Présélectionnée pour la visite de site.",
        )
        if data.get("status") != "SHORTLISTED":
            raise StepFailure(f"Statut non appliqué : {data.get('status')}")
        return data

    company_data = _company()
    company_profile = company_data
    _brand_assets()
    _documents()
    _realization()
    _verification()
    _apply()
    _review()

    # ------------------------------------------------------- abonnement & paiement
    print("\nAbonnement, facturation et encaissement")

    @step("Souscription à l'offre Pro (prix venant du backend)")
    def _subscribe():
        plans = call("GET", "/plans/")["results"]
        plan = next((item for item in plans if item["code"] == "PRO"), None)
        if plan is None:
            raise StepFailure("Offre Pro absente : lancez `manage.py seed_kemta`.")
        if float(plan["price_xaf"]) <= 0:
            raise StepFailure("Le prix de l'offre Pro doit venir du backend (valeur nulle reçue).")
        return call("POST", "/subscriptions/mine/", token=company_account["token"], plan_code="PRO")

    @step("Paiement Mobile Money idempotent puis encaissement KEMTA")
    def _payment():
        invoices = call("GET", "/invoices/", token=company_account["token"])
        rows = invoices.get("results") or []
        if not rows:
            raise StepFailure("Aucune facture d'abonnement émise.")
        invoice = rows[0]
        key = f"smoke-{invoice['id']}-{int(time.time())}"
        first = call(
            "POST", "/payments/initiate/", token=company_account["token"],
            kind="INVOICE", provider="MTN_MOMO", invoice_id=invoice["id"],
            payer_phone=company_account["phone"], idempotency_key=key,
        )
        replay = call(
            "POST", "/payments/initiate/", token=company_account["token"],
            kind="INVOICE", provider="MTN_MOMO", invoice_id=invoice["id"],
            payer_phone=company_account["phone"], idempotency_key=key,
        )
        if first["payment"]["reference"] != replay["payment"]["reference"]:
            raise StepFailure("Idempotence non respectée : deux paiements créés pour la même clé.")
        confirmed = call(
            "POST", f"/admin/payments/{first['payment']['id']}/confirm/", token=admin["token"],
            reference=first["payment"]["reference"],
        )
        if confirmed["payment"]["status"] != "SUCCEEDED":
            raise StepFailure(f"Paiement non encaissé : {confirmed['payment']['status']}")
        summary = call("GET", "/invoices/summary/", token=company_account["token"])
        return {"payment": confirmed["payment"], "invoice_summary": summary}

    @step("Tableau de bord entreprise (espace BTP)")
    def _company_dashboard():
        data = call("GET", "/dashboard/?space=COMPANY", token=company_account["token"])
        if not data.get("company"):
            raise StepFailure("Espace entreprise non détecté.")
        return data

    @step("Tableau de bord back-office KEMTA")
    def _admin_dashboard():
        data = call("GET", "/dashboard/?space=ADMIN", token=admin["token"])
        if "statistics" not in data:
            raise StepFailure("Statistiques absentes du tableau de bord admin.")
        return data

    @step("Déconnexion (jeton révoqué)")
    def _logout():
        return call("POST", "/auth/logout/", token=client["token"], refresh=client["refresh"])

    _subscribe()
    _payment()
    _company_dashboard()
    _admin_dashboard()
    _logout()

    print("\n" + "─" * 68)
    print(f"Étapes réussies : {len(PASSED)}   |   échecs : {len(FAILED)}")
    if FAILED:
        print("\nPoints à corriger :")
        for label, error in FAILED:
            print(f"  • {label}\n      {error}")
        return 1
    print("Tous les parcours critiques répondent correctement. ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
