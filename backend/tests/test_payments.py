"""Paiements : idempotence, cloisonnement, webhooks signés, factures."""
from __future__ import annotations

import hashlib
import hmac
import json
from decimal import Decimal

import pytest
from django.conf import settings

from apps.payments.models import Invoice, InvoiceStatus, Payment, PaymentStatus
from tests.factories import make_project

pytestmark = pytest.mark.django_db

INITIATE = "/api/v1/payments/initiate/"


def test_manual_payment_initiation_returns_instructions(api, authed, customer):
    project = make_project(customer=customer)
    authed(customer)
    response = api.post(
        INITIATE,
        {
            "kind": "MILESTONE",
            "provider": "MANUAL",
            "amount_xaf": 2_500_000,
            "project_id": project.pk,
            "idempotency_key": "clic-bouton-001",
        },
        format="json",
    )
    assert response.status_code == 201, response.content
    body = response.json()
    assert body["payment"]["reference"].startswith("KEMTA-PAY-")
    assert body["payment"]["status"] == "PENDING"
    assert "KEMTA" in body["message"]
    assert body["next_step"]


def test_payment_initiation_is_idempotent(api, authed, customer):
    """Un double clic ne doit jamais créer deux encaissements."""
    authed(customer)
    payload = {
        "kind": "MILESTONE",
        "provider": "MANUAL",
        "amount_xaf": 500_000,
        "idempotency_key": "double-clic-42",
    }
    first = api.post(INITIATE, payload, format="json")
    second = api.post(INITIATE, payload, format="json")
    assert first.status_code == second.status_code == 201
    assert first.json()["payment"]["reference"] == second.json()["payment"]["reference"]
    assert Payment.objects.filter(reference=first.json()["payment"]["reference"]).count() == 1


def test_payment_amount_must_be_positive(api, authed, customer):
    authed(customer)
    response = api.post(
        INITIATE,
        {"kind": "MILESTONE", "provider": "MANUAL", "amount_xaf": 0},
        format="json",
    )
    assert response.status_code == 400


def test_customer_cannot_pay_another_customers_invoice(api, authed, customer):
    other = type(customer).objects.create_user(
        phone="+237655000444", password="Kemta!2026test", role="CUSTOMER",
        first_name="Serge", last_name="Mbianda",
    )
    invoice = Invoice.objects.create(
        number="KEMTA-INV-2026-000777",
        customer=other,
        kind="SERVICE_FEE",
        subtotal_xaf=Decimal("150000"),
        total_xaf=Decimal("150000"),
        status=InvoiceStatus.SENT,
    )
    authed(customer)
    response = api.post(
        INITIATE,
        {"kind": "INVOICE", "provider": "MANUAL", "invoice_id": invoice.pk},
        format="json",
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_admin_confirms_manual_payment_and_invoice_is_settled(api, authed, customer, admin_user):
    invoice = Invoice.objects.create(
        number="KEMTA-INV-2026-000778",
        customer=customer,
        kind="SERVICE_FEE",
        subtotal_xaf=Decimal("250000"),
        total_xaf=Decimal("250000"),
        status=InvoiceStatus.SENT,
    )
    authed(customer)
    created = api.post(
        INITIATE,
        {"kind": "INVOICE", "provider": "MANUAL", "invoice_id": invoice.pk},
        format="json",
    ).json()
    payment_id = created["payment"]["id"]

    authed(admin_user)
    confirmed = api.post(
        f"/api/v1/admin/payments/{payment_id}/confirm/",
        {"provider_reference": "VIR-2026-0912"},
        format="json",
    )
    assert confirmed.status_code == 200, confirmed.content
    assert confirmed.json()["payment"]["status"] == PaymentStatus.SUCCEEDED

    invoice.refresh_from_db()
    assert invoice.status == InvoiceStatus.PAID
    assert Decimal(invoice.balance_xaf) == Decimal("0")

    # Rejouer la confirmation ne double pas l'encaissement.
    again = api.post(f"/api/v1/admin/payments/{payment_id}/confirm/", {}, format="json")
    assert again.status_code == 200
    assert Payment.objects.filter(invoice=invoice, status=PaymentStatus.SUCCEEDED).count() == 1


def test_webhook_refuses_an_unsigned_notification(api, customer):
    """Sans signature valide, aucune confirmation de paiement n'est acceptée."""
    response = api.post(
        "/api/v1/payments/webhook/MTN_MOMO/",
        {"id": "evt-001", "reference": "KEMTA-PAY-2026-000001", "status": "SUCCESSFUL"},
        format="json",
    )
    assert response.status_code == 200  # on accuse réception sans traiter
    assert response.json()["processed"] is False
    assert Payment.objects.filter(status=PaymentStatus.SUCCEEDED).count() == 0


def test_webhook_accepts_a_correctly_signed_notification(api, authed, customer, settings):
    settings.PAYMENT_WEBHOOK_SECRET = "secret-de-test"
    authed(customer)
    payment = api.post(
        INITIATE,
        {
            "kind": "MILESTONE",
            "provider": "MTN_MOMO",
            "amount_xaf": 100_000,
            "payer_phone": customer.phone,
            "idempotency_key": "webhook-001",
        },
        format="json",
    ).json()["payment"]

    payload = {
        "id": "evt-42",
        "type": "payment.success",
        "reference": payment["reference"],
        "status": "SUCCESSFUL",
        "amount": 100_000,
        "transactionId": "MP26091XYZ",
    }
    raw = json.dumps(payload).encode()
    signature = hmac.new(b"secret-de-test", raw, hashlib.sha256).hexdigest()
    response = api.post(
        "/api/v1/payments/webhook/MTN_MOMO/",
        data=raw,
        content_type="application/json",
        HTTP_X_KEMTA_SIGNATURE=signature,
    )
    assert response.status_code == 200, response.content
    assert response.json()["processed"] is True

    payment_obj = Payment.objects.get(reference=payment["reference"])
    assert payment_obj.status == PaymentStatus.SUCCEEDED

    # Rejeu du même événement : il n'est pas réappliqué (une seule transaction).
    replay = api.post(
        "/api/v1/payments/webhook/MTN_MOMO/",
        data=raw,
        content_type="application/json",
        HTTP_X_KEMTA_SIGNATURE=signature,
    )
    assert replay.status_code == 200
    payment_obj.refresh_from_db()
    assert payment_obj.status == PaymentStatus.SUCCEEDED
    assert payment_obj.transactions.count() == 1

    from apps.payments.models import WebhookEvent

    assert WebhookEvent.objects.filter(event_id="evt-42").count() == 1


def test_customer_sees_only_its_own_payments(api, authed, customer):
    """Le solde et l'historique d'un client ne doivent jamais fuiter chez un autre."""
    from apps.accounts.models import Role, User

    other = User.objects.create_user(
        phone="+237655000555", password="Kemta!2026test", role=Role.CUSTOMER,
        first_name="Alice", last_name="Ngono",
    )
    authed(other)
    created = api.post(
        INITIATE,
        {"kind": "MILESTONE", "provider": "MANUAL", "amount_xaf": 90_000,
         "idempotency_key": "autre-client"},
        format="json",
    )
    assert created.status_code == 201, created.content
    foreign_reference = created.json()["payment"]["reference"]

    authed(customer)
    response = api.get("/api/v1/payments/")
    assert response.status_code == 200
    references = {item["reference"] for item in response.json()["results"]}
    assert foreign_reference not in references
    assert settings.KEMTA_SUPPORT_EMAIL
