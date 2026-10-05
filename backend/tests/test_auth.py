"""Authentification par téléphone : OTP SMS, connexion, mot de passe.

Ces tests protègent le point d'entrée le plus sensible du produit : sans
téléphone vérifié, aucun accès aux projets, budgets et preuves d'un client.

Rappel de sécurité vérifié ici : le code OTP n'est jamais stocké en clair et
n'est renvoyé au client que si `DEBUG` **et** `OTP_DEV_ECHO` sont actifs.
"""
from __future__ import annotations

import pytest
from django.core.cache import cache

from apps.accounts.models import OTPVerification

pytestmark = pytest.mark.django_db

REGISTER = "/api/v1/auth/otp/request/"
VERIFY = "/api/v1/auth/otp/verify/"

STRONG_PASSWORD = "Kemta!2026fort"


@pytest.fixture(autouse=True)
def isolated_cache():
    """Le cache n'est pas rembobiné entre les tests : on l'isole explicitement.

    Sans cela, le délai de refroidissement OTP d'un test bloquerait le suivant.
    """
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def dev_echo(settings):
    """Active l'écho du code OTP, comme sur un poste de développement."""
    settings.DEBUG = True
    settings.OTP_DEV_ECHO = True
    return settings


def request_otp(api, phone: str, purpose: str = "REGISTER") -> dict:
    response = api.post(REGISTER, {"phone": phone, "purpose": purpose}, format="json")
    assert response.status_code == 200, response.content
    return response.json()


def otp_code(api, phone: str, purpose: str = "REGISTER") -> str:
    """Demande un code et le récupère par l'écho de développement."""
    body = request_otp(api, phone, purpose)
    assert body.get("dev_mode") is True, body
    code = body.get("dev_code")
    assert code, "Le code de développement doit accompagner la réponse en mode test"
    return code


def pending_code(phone: str, purpose: str = "REGISTER") -> str:
    """Lit le code déjà envoyé (mode développement) sans relancer d'envoi.

    Redemander un code pour le même numéro déclencherait le délai de
    refroidissement de 45 secondes : on lit donc l'écho du dernier SMS.
    """
    from apps.accounts.services import otp as otp_service
    from common.utils import normalize_phone

    code = otp_service.dev_echo_code(normalize_phone(phone), purpose)
    assert code, f"Aucun code de développement en attente pour {purpose}"
    return code


def verify(api, phone: str, code: str, purpose: str = "REGISTER") -> str:
    response = api.post(VERIFY, {"phone": phone, "purpose": purpose, "code": code}, format="json")
    assert response.status_code == 200, response.content
    return response.json()["verification_ticket"]


def test_otp_request_normalises_phone_and_enforces_cooldown(api):
    """Un numéro local devient international et deux envois coup sur coup sont bloqués."""
    first = api.post(REGISTER, {"phone": "650112233", "purpose": "REGISTER"}, format="json")
    assert first.status_code == 200, first.content
    body = first.json()
    assert body["phone_display"].startswith("+237")
    assert body["expires_in"] > 0
    assert body["attempts_allowed"] >= 3

    second = api.post(REGISTER, {"phone": "+237650112233", "purpose": "REGISTER"}, format="json")
    assert second.status_code == 409
    assert "secondes" in second.json()["error"]["message"]


def test_otp_code_is_never_exposed_without_debug(api, settings):
    """En configuration réelle, l'API ne divulgue ni le code ni un mode démo."""
    settings.DEBUG = False
    settings.OTP_DEV_ECHO = False
    body = request_otp(api, "+237650112234")
    assert "dev_code" not in body
    assert "dev_mode" not in body

    otp = OTPVerification.objects.filter(purpose="REGISTER").latest("created_at")
    assert otp.code_hash and not otp.code_hash.isdigit()  # empreinte, jamais le code


def test_otp_request_requires_valid_cameroonian_number(api):
    for invalid in ["123", "abc", "+23760000", ""]:
        response = api.post(REGISTER, {"phone": invalid, "purpose": "REGISTER"}, format="json")
        assert response.status_code == 400, invalid


def test_registration_rejects_phone_already_used(api, customer):
    response = api.post(REGISTER, {"phone": customer.phone, "purpose": "REGISTER"}, format="json")
    assert response.status_code == 400
    message = str(response.json()).lower()
    assert "existe" in message or "déjà" in message or "connexion" in message


def test_registration_flow_creates_customer_with_verified_phone(api, dev_echo):
    """Parcours complet : code SMS → inscription → accès aux espaces."""
    phone = "+237659887711"
    ticket = verify(api, phone, otp_code(api, phone))

    created = api.post(
        "/api/v1/auth/register/",
        {
            "phone": phone,
            "verification_ticket": ticket,
            "password": STRONG_PASSWORD,
            "password_confirm": STRONG_PASSWORD,
            "first_name": "Aïcha",
            "last_name": "Mbarga",
            "city": "Bafoussam",
            "terms_accepted": True,
        },
        format="json",
    )
    assert created.status_code == 201, created.content
    body = created.json()
    assert body["user"]["phone_verified"] is True
    assert body["user"]["first_name"] == "Aïcha"

    api.credentials(HTTP_AUTHORIZATION=f"Bearer {body['access']}")
    me = api.get("/api/v1/auth/me/")
    assert me.status_code == 200
    assert me.json()["spaces"][0]["key"] == "customer"


def test_registration_rejects_weak_password(api, dev_echo):
    phone = "+237659887712"
    ticket = verify(api, phone, otp_code(api, phone))
    response = api.post(
        "/api/v1/auth/register/",
        {
            "phone": phone,
            "verification_ticket": ticket,
            "password": "azerty",
            "password_confirm": "azerty",
            "first_name": "Ngo",
            "last_name": "Bello",
            "terms_accepted": True,
        },
        format="json",
    )
    assert response.status_code == 400
    assert "mot de passe" in str(response.json()).lower()


def test_registration_ticket_is_single_use_and_bound_to_one_phone(api, dev_echo):
    """Un ticket d'OTP ne doit servir qu'une fois, et pour le numéro vérifié.

    Sinon un code intercepté permettrait de créer plusieurs comptes, ou un
    compte sur un numéro qui n'a jamais reçu de SMS.
    """
    phone = "+237659887713"
    ticket = verify(api, phone, otp_code(api, phone))
    payload = {
        "phone": phone,
        "verification_ticket": ticket,
        "password": STRONG_PASSWORD,
        "password_confirm": STRONG_PASSWORD,
        "first_name": "Double",
        "last_name": "Compte",
        "terms_accepted": True,
    }
    assert api.post("/api/v1/auth/register/", payload, format="json").status_code == 201

    # Rejeu strict : le numéro est déjà inscrit (400) et le ticket est consommé.
    assert api.post("/api/v1/auth/register/", payload, format="json").status_code == 400

    # Ticket détourné vers un autre numéro : refusé pour règle métier.
    hijack = {**payload, "phone": "+237659887799", "verification_ticket": ticket}
    response = api.post("/api/v1/auth/register/", hijack, format="json")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "business_rule"


def test_wrong_code_is_refused_with_human_message(api, dev_echo):
    phone = "+237659887722"
    otp_code(api, phone)
    wrong = api.post(VERIFY, {"phone": phone, "purpose": "REGISTER", "code": "000000"}, format="json")
    assert wrong.status_code == 409
    message = wrong.json()["error"]["message"].lower()
    assert "code" in message
    assert not message.startswith("invalid")


def test_password_login_and_access_log(api, customer):
    login = api.post(
        "/api/v1/auth/login/", {"phone": customer.phone, "password": "Kemta!2026test"}, format="json"
    )
    assert login.status_code == 200
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {login.json()['access']}")
    assert api.get("/api/v1/auth/me/").status_code == 200

    logs = api.get("/api/v1/auth/logs/")
    assert logs.status_code == 200  # le titulaire peut consulter ses connexions


def test_login_with_wrong_password_does_not_reveal_account_existence(api, customer):
    """Le message d'erreur doit être identique pour un mauvais mot de passe et un
    numéro inconnu : sinon l'API devient un annuaire de clients."""
    wrong_password = api.post(
        "/api/v1/auth/login/", {"phone": customer.phone, "password": "MauvaisMotDePasse1"}, format="json"
    )
    unknown_phone = api.post(
        "/api/v1/auth/login/", {"phone": "+237659887733", "password": "MauvaisMotDePasse1"}, format="json"
    )
    assert wrong_password.status_code == unknown_phone.status_code == 409
    assert wrong_password.json()["error"]["message"] == unknown_phone.json()["error"]["message"]
    assert wrong_password.json()["error"]["code"] == unknown_phone.json()["error"]["code"]


def test_me_requires_authentication(api):
    assert api.get("/api/v1/auth/me/").status_code == 401


def test_password_reset_rotates_password(api, customer, dev_echo):
    phone = customer.phone
    asked = api.post("/api/v1/auth/password/reset/", {"phone": phone}, format="json")
    assert asked.status_code == 200
    assert phone[-4:] not in asked.json()["message"]  # réponse neutre

    ticket = verify(api, phone, pending_code(phone, "PASSWORD_RESET"), "PASSWORD_RESET")

    reset = api.post(
        "/api/v1/auth/password/reset/confirm/",
        {
            "phone": phone,
            "verification_ticket": ticket,
            "password": "NouveauMot!2026",
            "password_confirm": "NouveauMot!2026",
        },
        format="json",
    )
    assert reset.status_code == 200, reset.content

    customer.refresh_from_db()
    assert customer.check_password("NouveauMot!2026")
    assert api.post("/api/v1/auth/login/", {"phone": phone, "password": "NouveauMot!2026"}, format="json").status_code == 200


def test_weak_password_is_refused_on_reset(api, customer, dev_echo):
    phone = customer.phone
    api.post("/api/v1/auth/password/reset/", {"phone": phone}, format="json")
    ticket = verify(api, phone, pending_code(phone, "PASSWORD_RESET"), "PASSWORD_RESET")
    response = api.post(
        "/api/v1/auth/password/reset/confirm/",
        {
            "phone": phone,
            "verification_ticket": ticket,
            "password": "12345678",
            "password_confirm": "12345678",
        },
        format="json",
    )
    assert response.status_code == 400
    assert "mot de passe" in str(response.json()).lower()


def test_otp_is_single_use(api, dev_echo):
    """Un code rejoué après succès doit être refusé (anti-rejeu)."""
    phone = "+237659887744"
    code = otp_code(api, phone)
    assert api.post(VERIFY, {"phone": phone, "purpose": "REGISTER", "code": code}, format="json").status_code == 200
    replay = api.post(VERIFY, {"phone": phone, "purpose": "REGISTER", "code": code}, format="json")
    assert replay.status_code == 409
    assert "déjà" in replay.json()["error"]["message"]
