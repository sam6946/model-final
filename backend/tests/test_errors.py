"""Contrat de langue des erreurs.

KEMTA est un produit francophone : ses messages d'erreur sont affichés tels
quels dans l'interface. Une régression a été constatée en production — un
navigateur configuré en anglais recevait « Authentication credentials were not
provided. » — parce que ``LocaleMiddleware`` suivait l'en-tête
``Accept-Language``. Ces tests verrouillent le comportement attendu : la langue
du navigateur ne change jamais celle des réponses de l'API.
"""
from __future__ import annotations

import pytest

ANGLISH_BROWSER = "en-US,en;q=0.9"


def _message(response) -> str:
    return response.json()["error"]["message"]


@pytest.mark.parametrize("accept_language", [None, "en-US,en;q=0.9", "de-DE,de;q=0.8"])
def test_auth_error_is_french_whatever_the_browser_language(api, accept_language):
    """Un visiteur non connecté reçoit un message français, en 401."""
    headers = {"HTTP_ACCEPT_LANGUAGE": accept_language} if accept_language else {}
    response = api.get("/api/v1/auth/me/", **headers)

    assert response.status_code == 401
    payload = response.json()["error"]
    assert payload["code"] == "not_authenticated"
    message = payload["message"]
    assert "credentials were not provided" not in message.lower()
    assert "authentification" in message.lower() or "connecté" in message.lower()
    assert response["Content-Language"] == "fr"


def test_invalid_token_error_is_french(api):
    """Un jeton invalide produit une explication compréhensible, pas du charabia."""
    response = api.get(
        "/api/v1/auth/me/",
        HTTP_AUTHORIZATION="Bearer jeton.totalement.invalide",
        HTTP_ACCEPT_LANGUAGE=ANGLISH_BROWSER,
    )

    assert response.status_code == 401
    message = _message(response)
    assert "not valid for any token type" not in message.lower()
    assert "session" in message.lower()
    assert "reconnect" in message.lower()


def test_forbidden_error_is_french(api, authed, customer):
    """Un accès refusé est expliqué en français (403 du back-office)."""
    authed(customer)
    response = api.get("/api/v1/admin/projects/", HTTP_ACCEPT_LANGUAGE=ANGLISH_BROWSER)

    assert response.status_code == 403
    message = _message(response)
    assert "you do not have permission" not in message.lower()
    assert "permission" in message.lower() or "autoris" in message.lower()


def test_not_found_error_is_french(api, authed, customer):
    """Une ressource absente renvoie une phrase française, pas « Not found. »."""
    authed(customer)
    response = api.get("/api/v1/projects/kemta-inexistant/", HTTP_ACCEPT_LANGUAGE=ANGLISH_BROWSER)

    assert response.status_code == 404
    assert response["Content-Type"].startswith("application/json")
    message = _message(response)
    assert message.strip().lower() not in {"not found.", "not found"}
    assert "existe pas" in message.lower() or "supprimée" in message.lower()


def test_unknown_api_address_answers_json(api):
    """Une adresse d'API inconnue répond en JSON, jamais la page de l'application.

    Sans cela un client d'API recevait du HTML avec un code 200 : impossible de
    distinguer une erreur d'adresse d'une réponse valide.
    """
    response = api.get("/api/v1/adresse/qui/n/existe/pas/", HTTP_ACCEPT_LANGUAGE=ANGLISH_BROWSER)

    assert response.status_code == 404
    assert response["Content-Type"].startswith("application/json")
    assert "existe pas" in _message(response)


def test_business_message_is_never_replaced(api, customer):
    """Les messages rédigés par KEMTA restent intacts : eux seuls sont affichés."""
    response = api.post(
        "/api/v1/auth/login/",
        {"phone": customer.phone, "password": "MauvaisMotDePasse!2026"},
        format="json",
        HTTP_ACCEPT_LANGUAGE=ANGLISH_BROWSER,
    )

    assert response.status_code in (400, 401, 409)
    message = _message(response)
    assert "mot de passe" in message.lower()
    assert "incorrect" in message.lower()


def test_expired_refresh_token_is_a_clean_401(api):
    """Un jeton de rafraîchissement inexploitable ne doit jamais produire un 500.

    Une session ancienne (jeton expiré, révoqué, ou signé par un autre
    environnement) est un cas courant : l'utilisateur doit recevoir un 401 clair
    invitant à se reconnecter, pas un incident technique.
    """
    response = api.post(
        "/api/v1/auth/token/refresh/",
        {"refresh": "jeton.inexploitable.xyz"},
        format="json",
        HTTP_ACCEPT_LANGUAGE=ANGLISH_BROWSER,
    )

    assert response.status_code == 401, response.content
    payload = response.json()["error"]
    assert payload["code"] == "token_not_valid"
    assert "session" in payload["message"].lower()
