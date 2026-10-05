"""Paiements : abstraction fournisseur, idempotence, facturation.

Chaque fournisseur (MTN MoMo, Orange Money, carte, virement) implémente la même
interface. Le reste de l'application ne connaît que cette interface : ajouter un
prestataire = ajouter une classe, sans toucher aux modèles ni aux vues.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import uuid
from dataclasses import dataclass
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.activities.services import record_activity
from apps.payments.models import (
    Invoice,
    InvoiceStatus,
    Payment,
    PaymentKind,
    PaymentProvider,
    PaymentStatus,
    WebhookEvent,
)
from common.utils import humanize_amount, mask_phone

logger = logging.getLogger("kemta.payments")


@dataclass(frozen=True)
class PaymentIntent:
    """Résultat d'une demande d'encaissement auprès d'un fournisseur."""

    provider: str
    provider_reference: str
    status: str
    checkout_url: str = ""
    instructions: str = ""
    metadata: dict | None = None


class PaymentGateway:
    """Interface commune à tous les prestataires de paiement."""

    provider_code: str = PaymentProvider.OTHER
    supports_async = False  # True si la confirmation arrive par webhook

    def create_payment(self, *, payment: Payment, phone: str = "", email: str = "") -> PaymentIntent:
        raise NotImplementedError

    def verify_webhook(self, *, payload: bytes, signature: str) -> bool:
        """Vérifie l'authenticité d'une notification fournisseur."""
        secret = settings.PAYMENT_WEBHOOK_SECRET
        if not secret:
            # Pas de secret configuré : on refuse par défaut plutôt que de
            # faire confiance à une requête non authentifiée.
            return False
        expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, (signature or "").strip())

    def parse_webhook(self, payload: dict) -> dict:
        """Normalise la charge utile fournisseur."""
        return {
            "event_id": str(payload.get("id") or payload.get("event_id") or uuid.uuid4()),
            "event_type": payload.get("type") or payload.get("status") or "unknown",
            "reference": payload.get("reference") or payload.get("externalId") or "",
            "status": (payload.get("status") or "").upper(),
            "amount": payload.get("amount"),
            "transaction_id": payload.get("transaction_id") or payload.get("transactionId") or "",
            "raw": payload,
        }


class ManualPaymentGateway(PaymentGateway):
    """Virement bancaire ou espèces : le back-office confirme l'encaissement."""

    provider_code = PaymentProvider.MANUAL

    def create_payment(self, *, payment: Payment, phone: str = "", email: str = "") -> PaymentIntent:
        instructions = (
            f"Référence à indiquer : {payment.reference}. "
            f"Compte KEMTA SUIVI SARL — Afriland First Bank — IBAN CM21 1000 2000 3000 4000 5000 678. "
            "Envoyez la preuve de virement à {email_support}."
        ).format(email_support=settings.KEMTA_SUPPORT_EMAIL)
        return PaymentIntent(
            provider=self.provider_code,
            provider_reference=f"MANUAL-{payment.reference}",
            status=PaymentStatus.PENDING,
            instructions=instructions,
            metadata={"type": "offline"},
        )


class MobileMoneyGateway(PaymentGateway):
    """Paiement Mobile Money (MTN MoMo, Orange Money) via agrégateur configurable.

    Le protocole exact dépend de l'agrégateur (campay, flutterwave, MTN direct).
    Le contrat retenu ici : ``POST {PAYMENT_BASE_URL}/collect`` avec ``{amount,
    currency, phone, reference}`` et une clé d'API — ce qui couvre la majorité
    des agrégateurs africains. Une fois le compte partenaire ouvert, seul
    ``PAYMENT_PROVIDER`` change dans .env.
    """

    provider_code = PaymentProvider.MTN_MOMO
    supports_async = True

    def create_payment(self, *, payment: Payment, phone: str = "", email: str = "") -> PaymentIntent:
        if not phone:
            raise ValueError(
                "Un numéro de téléphone est nécessaire pour un paiement Mobile Money."
            )
        if not settings.PAYMENT_API_KEY or not settings.PAYMENT_BASE_URL:
            # Pas de passerelle configurée : on enregistre l'intention et on
            # donne les instructions, plutôt que d'échouer silencieusement.
            return PaymentIntent(
                provider=self.provider_code,
                provider_reference=f"PENDING-{payment.reference}",
                status=PaymentStatus.PENDING,
                instructions=(
                    f"Paiement Mobile Money en attente d'activation sur le compte marchand KEMTA. "
                    f"Référence : {payment.reference}. Contactez le {settings.KEMTA_SUPPORT_PHONE} "
                    "pour finaliser immédiatement."
                ),
                metadata={"gateway_configured": False},
            )

        import requests

        url = f"{settings.PAYMENT_BASE_URL.rstrip('/')}/collect"
        headers = {"Authorization": f"Bearer {settings.PAYMENT_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "amount": int(payment.amount_xaf),
            "currency": payment.currency,
            "phone": phone,
            "reference": payment.reference,
            "description": f"KEMTA {payment.get_kind_display()}",
        }
        try:
            response = requests.post(
                url, json=payload, headers=headers,
                timeout=getattr(settings, "PAYMENT_TIMEOUT_SECONDS", 20),
            )
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            logger.error(
                "payment_gateway_error",
                extra={"payment": payment.reference, "error": str(exc)[:200]},
            )
            return PaymentIntent(
                provider=self.provider_code,
                provider_reference="",
                status=PaymentStatus.FAILED,
                instructions="La demande de paiement n'a pas pu aboutir. Réessayez ou choisissez un autre moyen.",
                metadata={"error": str(exc)[:200]},
            )
        return PaymentIntent(
            provider=self.provider_code,
            provider_reference=str(data.get("id") or data.get("reference") or ""),
            status=PaymentStatus.PROCESSING,
            checkout_url=data.get("payment_url") or data.get("checkout_url") or "",
            instructions=(
                "Validez le paiement sur votre téléphone : saisissez le code reçu par SMS "
                "de votre opérateur Mobile Money."
            ),
            metadata={"gateway_response": data},
        )


class OrangeMoneyGateway(MobileMoneyGateway):
    provider_code = PaymentProvider.ORANGE_MONEY


class CardGateway(PaymentGateway):
    """Carte bancaire (agrégateur type Stripe/CinetPay) : redirection hébergée."""

    provider_code = PaymentProvider.CARD
    supports_async = True

    def create_payment(self, *, payment: Payment, phone: str = "", email: str = "") -> PaymentIntent:
        if not settings.PAYMENT_API_KEY or not settings.PAYMENT_BASE_URL:
            return PaymentIntent(
                provider=self.provider_code,
                provider_reference="",
                status=PaymentStatus.PENDING,
                instructions=(
                    "Le paiement par carte sera disponible très prochainement. "
                    f"Choisissez Mobile Money ou contactez le {settings.KEMTA_SUPPORT_PHONE}."
                ),
                metadata={"gateway_configured": False},
            )
        # Avec une passerelle configurée, on renvoie le lien hébergé.
        return PaymentIntent(
            provider=self.provider_code,
            provider_reference=f"CARD-{payment.reference}",
            status=PaymentStatus.PROCESSING,
            checkout_url=f"{settings.PAYMENT_BASE_URL.rstrip('/')}/checkout/{payment.reference}",
            instructions="Vous allez être redirigé vers la page de paiement sécurisée.",
        )


GATEWAYS: dict[str, type[PaymentGateway]] = {
    PaymentProvider.MANUAL: ManualPaymentGateway,
    PaymentProvider.BANK_TRANSFER: ManualPaymentGateway,
    PaymentProvider.MTN_MOMO: MobileMoneyGateway,
    PaymentProvider.ORANGE_MONEY: OrangeMoneyGateway,
    PaymentProvider.CARD: CardGateway,
    PaymentProvider.OTHER: ManualPaymentGateway,
}


def get_gateway(provider: str) -> PaymentGateway:
    gateway_class = GATEWAYS.get(provider, ManualPaymentGateway)
    gateway = gateway_class()
    if provider in {PaymentProvider.MTN_MOMO, PaymentProvider.ORANGE_MONEY}:
        gateway.provider_code = provider  # conserve l'opérateur choisi par le client
    return gateway


@transaction.atomic
def initiate_payment(
    *,
    kind: str,
    provider: str,
    amount_xaf: Decimal,
    actor,
    payer=None,
    company=None,
    project=None,
    invoice: Invoice | None = None,
    subscription=None,
    payer_phone: str = "",
    payer_email: str = "",
    idempotency_key: str = "",
    metadata: dict | None = None,
) -> Payment:
    """Crée une intention de paiement idempotente et interroge le fournisseur.

    L'idempotence est garantie par ``idempotency_key`` : un double clic sur
    « Payer » ne crée jamais deux débits, même si le client renvoie le
    formulaire plusieurs fois.
    """
    amount = Decimal(amount_xaf or 0)
    if amount < settings.PAYMENT_MIN_AMOUNT_XAF:
        raise ValueError(
            f"Le montant minimum de paiement est de {humanize_amount(settings.PAYMENT_MIN_AMOUNT_XAF)}."
        )
    if invoice is not None and invoice.is_settled:
        raise ValueError("Cette facture est déjà réglée : aucun paiement n'est nécessaire.")

    key = idempotency_key or uuid.uuid4().hex
    existing = Payment.objects.filter(idempotency_key=key).first()
    if existing is not None:
        logger.info("payment_idempotent_replay", extra={"reference": existing.reference})
        return existing

    payment = Payment.objects.create(
        kind=kind,
        provider=provider,
        status=PaymentStatus.PENDING,
        amount_xaf=amount,
        currency=settings.PAYMENT_CURRENCY,
        payer=payer or (actor if getattr(actor, "is_authenticated", False) else None),
        company=company,
        project=project,
        invoice=invoice,
        subscription=subscription,
        idempotency_key=key,
        payer_phone=payer_phone,
        payer_email=(payer_email or getattr(payer or actor, "email", "") or ""),
        initiated_by=actor if getattr(actor, "is_authenticated", False) else None,
        metadata=metadata or {},
        expires_at=timezone.now() + timezone.timedelta(hours=24),
    )

    try:
        intent = get_gateway(provider).create_payment(
            payment=payment, phone=payer_phone, email=payment.payer_email
        )
    except ValueError as exc:
        payment.mark_failed(reason=str(exc))
        raise

    payment.provider_reference = intent.provider_reference
    payment.status = intent.status
    payment.checkout_url = intent.checkout_url
    payment.instructions = intent.instructions
    payment.metadata = {**(payment.metadata or {}), **(intent.metadata or {})}
    payment.save(update_fields=[
        "provider_reference", "status", "checkout_url", "instructions", "metadata", "updated_at",
    ])

    if intent.status == PaymentStatus.FAILED:
        payment.mark_failed(reason=intent.instructions or "Échec du fournisseur")

    record_activity(
        verb="PAYMENT_INITIATED" if intent.status != PaymentStatus.FAILED else "PAYMENT_FAILED",
        message=f"Paiement {payment.reference} — {humanize_amount(amount)} ({payment.get_provider_display()})",
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        company=company,
        project=project,
        entity_type="Payment",
        entity_id=payment.pk,
        visibility="CUSTOMER",
        payload={"reference": payment.reference, "amount": float(amount), "provider": provider},
    )
    logger.info(
        "payment_initiated",
        extra={
            "reference": payment.reference,
            "provider": provider,
            "amount": float(amount),
            "phone": mask_phone(payer_phone) if payer_phone else "",
        },
    )
    return payment


@transaction.atomic
def confirm_payment(*, payment: Payment, actor, provider_reference: str = "") -> Payment:
    """Confirmation manuelle par le back-office (virement, espèces, MoMo hors ligne)."""
    payment.mark_succeeded(provider_reference=provider_reference or payment.reference)
    on_payment_succeeded(payment)
    return payment


def on_payment_succeeded(payment: Payment) -> None:
    """Effets métier d'un encaissement (abonnement, facture, notification)."""
    from apps.notifications.services import notify
    from common.constants import NotificationType

    if payment.subscription_id:
        from apps.subscriptions.services import activate_on_payment

        activate_on_payment(payment=payment)

    if payment.invoice_id and payment.invoice.customer_id:
        notify(
            recipient=payment.invoice.customer,
            notification_type=NotificationType.PAYMENT,
            title="Paiement enregistré",
            body=(
                f"Nous avons bien reçu {humanize_amount(payment.amount_xaf)} pour la facture "
                f"{payment.invoice.number}. Solde restant : {humanize_amount(payment.invoice.balance_xaf)}."
            ),
            action_url="/espace/paiements",
            action_label="Voir mes factures",
            entity_type="Payment",
            entity_id=payment.pk,
            payload={"reference": payment.reference, "amount_label": humanize_amount(payment.amount_xaf)},
            dedupe_key=f"payment:{payment.pk}:confirmed",
            also_sms=True,
        )
    elif payment.payer_id:
        notify(
            recipient=payment.payer,
            notification_type=NotificationType.PAYMENT,
            title="Paiement confirmé",
            body=f"Votre paiement {payment.reference} de {humanize_amount(payment.amount_xaf)} est confirmé.",
            action_url="/espace/paiements",
            action_label="Voir le détail",
            entity_type="Payment",
            entity_id=payment.pk,
            payload={"reference": payment.reference, "amount_label": humanize_amount(payment.amount_xaf)},
            dedupe_key=f"payment:{payment.pk}:confirmed",
        )

    record_activity(
        verb="PAYMENT_SUCCEEDED",
        message=f"Paiement encaissé : {humanize_amount(payment.amount_xaf)} ({payment.reference})",
        company=payment.company,
        project=payment.project,
        entity_type="Payment",
        entity_id=payment.pk,
        visibility="CUSTOMER",
        is_important=True,
        payload={"reference": payment.reference, "amount": float(payment.amount_xaf)},
    )

    # Le budget du projet se met à jour automatiquement après encaissement.
    if payment.project_id:
        payment.project.recalculate_finance()


@transaction.atomic
def handle_webhook(*, provider: str, payload: dict, raw_body: bytes, signature: str) -> WebhookEvent:
    """Enregistre puis traite une notification fournisseur, une seule fois."""
    gateway = get_gateway(provider)
    signature_valid = gateway.verify_webhook(payload=raw_body, signature=signature)
    normalized = gateway.parse_webhook(payload)

    event, created = WebhookEvent.objects.get_or_create(
        provider=provider,
        event_id=normalized["event_id"][:160],
        defaults={
            "event_type": normalized["event_type"][:80],
            "payload": normalized["raw"],
            "signature_valid": signature_valid,
        },
    )
    if not created:
        # Webhook rejoué par le fournisseur : on ne retraite pas.
        return event

    if not signature_valid and settings.PAYMENT_WEBHOOK_SECRET:
        event.error = "Signature invalide"
        event.save(update_fields=["error"])
        logger.warning("payment_webhook_invalid_signature", extra={"provider": provider})
        return event

    reference = normalized.get("reference") or ""
    payment = Payment.objects.filter(reference=reference).first()
    if payment is None:
        event.error = f"Paiement {reference} introuvable"
        event.save(update_fields=["error"])
        return event

    status_value = normalized.get("status") or ""
    try:
        if status_value in {"SUCCESS", "SUCCESSFUL", "PAID", "COMPLETED", "SUCCEEDED"}:
            payment.mark_succeeded(
                provider_reference=normalized.get("transaction_id") or payment.provider_reference,
                payload={**normalized["raw"], "_signature_verified": signature_valid},
            )
            on_payment_succeeded(payment)
        elif status_value in {"FAILED", "CANCELLED", "EXPIRED", "REJECTED"}:
            payment.mark_failed(reason=status_value, payload=normalized["raw"])
        event.processed = True
        event.processed_at = timezone.now()
        event.save(update_fields=["processed", "processed_at"])
    except Exception as exc:  # pragma: no cover
        event.error = str(exc)[:255]
        event.save(update_fields=["error"])
        logger.exception("payment_webhook_processing_failed", extra={"provider": provider})
    return event


def create_subscription_invoice(*, subscription, actor=None) -> Invoice:
    """Émet la facture d'abonnement correspondant à la période en cours."""
    plan = subscription.plan
    lines = [
        {
            "label": f"Abonnement KEMTA {plan.name} — {plan.get_interval_display()}",
            "quantity": 1,
            "unit_price": float(plan.price_xaf or 0),
            "total": float(plan.price_xaf or 0),
        }
    ]
    invoice = Invoice.objects.create(
        customer=subscription.company.owner_id and subscription.company.owner,
        company=subscription.company,
        subscription=subscription,
        kind=PaymentKind.SUBSCRIPTION,
        subtotal_xaf=plan.price_xaf or 0,
        tax_xaf=0,
        total_xaf=plan.price_xaf or 0,
        status=InvoiceStatus.SENT,
        lines=lines,
        issued_at=timezone.localdate(),
        due_at=timezone.localdate() + timezone.timedelta(days=7),
        notes="Merci d'indiquer la référence de la facture lors de votre paiement.",
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
    )
    record_activity(
        verb="INVOICE_CREATED",
        message=f"Facture {invoice.number} émise ({humanize_amount(invoice.total_xaf)})",
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        company=subscription.company,
        entity_type="Invoice",
        entity_id=invoice.pk,
        visibility="CUSTOMER",
    )
    return invoice
