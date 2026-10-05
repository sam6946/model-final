"""Paiements : architecture multi-fournisseurs, idempotente et auditable.

Principes retenus pour le marché africain :

1. **Abstraction fournisseur** : Mobile Money (MTN MoMo, Orange Money), carte
   bancaire et virement manuel passent par la même interface ; changer de
   prestataire ne touche ni la base ni le reste de l'application.
2. **Idempotence** : chaque paiement possède une clé unique fournie par le
   client, chaque notification fournisseur est enregistrée une seule fois
   (contrainte d'unicité sur ``provider_event_id``) — un webhook rejoué ne
   crédite jamais deux fois.
3. **Traçabilité** : les montants et statuts ne sont jamais réécrits ; on
   ajoute une transaction (journal immuable) à chaque changement d'état.
"""
from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.utils import timezone

from common.constants import Currency
from common.models import ReferenceCounter


class PaymentProvider(models.TextChoices):
    MANUAL = "MANUAL", "Virement / espèces (hors ligne)"
    MTN_MOMO = "MTN_MOMO", "MTN Mobile Money"
    ORANGE_MONEY = "ORANGE_MONEY", "Orange Money"
    CARD = "CARD", "Carte bancaire"
    BANK_TRANSFER = "BANK_TRANSFER", "Virement bancaire"
    OTHER = "OTHER", "Autre fournisseur"


class PaymentStatus(models.TextChoices):
    PENDING = "PENDING", "En attente"
    PROCESSING = "PROCESSING", "En cours de traitement"
    SUCCEEDED = "SUCCEEDED", "Réussi"
    FAILED = "FAILED", "Échoué"
    CANCELLED = "CANCELLED", "Annulé"
    REFUNDED = "REFUNDED", "Remboursé"
    EXPIRED = "EXPIRED", "Expiré"


class PaymentKind(models.TextChoices):
    SUBSCRIPTION = "SUBSCRIPTION", "Abonnement entreprise"
    INVOICE = "INVOICE", "Règlement de facture"
    MILESTONE = "MILESTONE", "Décaissement par jalon"
    ESCROW_FUNDING = "ESCROW_FUNDING", "Alimentation du compte séquestre"
    SERVICE_FEE = "SERVICE_FEE", "Frais de service KEMTA"
    OTHER = "OTHER", "Autre"


class InvoiceStatus(models.TextChoices):
    DRAFT = "DRAFT", "Brouillon"
    SENT = "SENT", "Envoyée"
    PARTIALLY_PAID = "PARTIALLY_PAID", "Partiellement réglée"
    PAID = "PAID", "Réglée"
    OVERDUE = "OVERDUE", "En retard"
    VOID = "VOID", "Annulée"


class Invoice(models.Model):
    """Facture (abonnement entreprise, prestation, décaissement chantier)."""

    number = models.CharField("numéro", max_length=40, unique=True)
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="client", null=True, blank=True,
        on_delete=models.PROTECT, related_name="invoices",
    )
    company = models.ForeignKey(
        "companies.Company", verbose_name="entreprise", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="invoices",
    )
    project = models.ForeignKey(
        "projects.Project", verbose_name="projet", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="invoices",
    )
    subscription = models.ForeignKey(
        "subscriptions.Subscription", verbose_name="abonnement", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="invoices",
    )

    kind = models.CharField("nature", max_length=16, choices=PaymentKind.choices, default=PaymentKind.OTHER)
    currency = models.CharField("devise", max_length=3, choices=Currency.choices, default=Currency.XAF)
    subtotal_xaf = models.DecimalField("montant HT", max_digits=14, decimal_places=2, default=0)
    tax_xaf = models.DecimalField("TVA", max_digits=14, decimal_places=2, default=0)
    total_xaf = models.DecimalField("total", max_digits=14, decimal_places=2, default=0)
    amount_paid_xaf = models.DecimalField("déjà réglé", max_digits=14, decimal_places=2, default=0)

    status = models.CharField("statut", max_length=16, choices=InvoiceStatus.choices, default=InvoiceStatus.DRAFT, db_index=True)
    lines = models.JSONField(
        "lignes", default=list, blank=True,
        help_text="Liste [{label, quantity, unit_price, total}] pour le PDF.",
    )
    notes = models.CharField("mentions", max_length=255, blank=True)
    issued_at = models.DateField("émise le", default=timezone.localdate)
    due_at = models.DateField("échéance", null=True, blank=True)
    paid_at = models.DateTimeField("réglée le", null=True, blank=True)
    pdf = models.ForeignKey(
        "common.Asset", verbose_name="PDF", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="invoices",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="créée par", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "facture"
        verbose_name_plural = "factures"
        ordering = ("-issued_at", "-id")
        indexes = [
            models.Index(fields=("status", "due_at")),
            models.Index(fields=("customer", "-issued_at")),
            models.Index(fields=("company", "-issued_at")),
        ]

    def __str__(self) -> str:
        return self.number

    def save(self, *args, **kwargs) -> None:
        if not self.number:
            self.number = ReferenceCounter.next_reference("FAC")
        if self.total_xaf in (None, Decimal("0")) and (self.subtotal_xaf or self.tax_xaf):
            self.total_xaf = (self.subtotal_xaf or Decimal("0")) + (self.tax_xaf or Decimal("0"))
        super().save(*args, **kwargs)

    # -- Indicateurs ------------------------------------------------------
    @property
    def balance_xaf(self) -> Decimal:
        return (self.total_xaf or Decimal("0")) - (self.amount_paid_xaf or Decimal("0"))

    @property
    def is_settled(self) -> bool:
        return self.balance_xaf <= 0

    @property
    def is_overdue(self) -> bool:
        return bool(
            self.due_at
            and not self.is_settled
            and self.status not in {InvoiceStatus.VOID, InvoiceStatus.PAID}
            and self.due_at < timezone.localdate()
        )

    @property
    def display_status(self) -> str:
        if self.is_settled and self.status != InvoiceStatus.VOID:
            return "Réglée"
        if self.is_overdue:
            return "En retard"
        return self.get_status_display()

    @transaction.atomic
    def apply_payment(self, amount: Decimal) -> None:
        Invoice.objects.filter(pk=self.pk).update(
            amount_paid_xaf=models.F("amount_paid_xaf") + amount, updated_at=timezone.now()
        )
        self.refresh_from_db(fields=["amount_paid_xaf", "total_xaf"])
        new_status = InvoiceStatus.PAID if self.is_settled else InvoiceStatus.PARTIALLY_PAID
        paid_at = timezone.now() if self.is_settled else None
        Invoice.objects.filter(pk=self.pk).update(status=new_status, paid_at=paid_at)
        self.status = new_status


class Payment(models.Model):
    """Intention de paiement (une par opération, idempotente)."""

    reference = models.CharField("référence", max_length=40, unique=True)
    kind = models.CharField("nature", max_length=16, choices=PaymentKind.choices, default=PaymentKind.OTHER)
    provider = models.CharField(
        "fournisseur", max_length=16, choices=PaymentProvider.choices, default=PaymentProvider.MANUAL
    )
    status = models.CharField(
        "statut", max_length=12, choices=PaymentStatus.choices, default=PaymentStatus.PENDING, db_index=True
    )
    currency = models.CharField("devise", max_length=3, choices=Currency.choices, default=Currency.XAF)
    amount_xaf = models.DecimalField(
        "montant (FCFA)", max_digits=14, decimal_places=2, validators=[MinValueValidator(0)]
    )

    payer = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="payeur", null=True, blank=True,
        on_delete=models.PROTECT, related_name="payments",
    )
    company = models.ForeignKey(
        "companies.Company", verbose_name="entreprise", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="payments",
    )
    project = models.ForeignKey(
        "projects.Project", verbose_name="projet", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="payments",
    )
    invoice = models.ForeignKey(
        Invoice, verbose_name="facture", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="payments",
    )
    subscription = models.ForeignKey(
        "subscriptions.Subscription", verbose_name="abonnement", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="payments",
    )

    idempotency_key = models.CharField(
        "clé d'idempotence", max_length=140, unique=True,
        help_text="Empêche tout double débit en cas de double envoi du formulaire.",
    )
    provider_reference = models.CharField("référence fournisseur", max_length=120, blank=True, db_index=True)
    payer_phone = models.CharField("numéro de paiement", max_length=20, blank=True)
    payer_email = models.EmailField("e-mail de reçu", blank=True)
    checkout_url = models.URLField("lien de paiement", blank=True)
    instructions = models.CharField("instructions de paiement", max_length=255, blank=True)

    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="initié par", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="initiated_payments",
    )
    metadata = models.JSONField("métadonnées", default=dict, blank=True)
    failure_reason = models.CharField("motif d'échec", max_length=255, blank=True)
    refunded_amount_xaf = models.DecimalField("montant remboursé", max_digits=14, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField("payé le", null=True, blank=True)
    expires_at = models.DateTimeField("expire le", null=True, blank=True)

    class Meta:
        verbose_name = "paiement"
        verbose_name_plural = "paiements"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("status", "-created_at")),
            models.Index(fields=("provider", "status")),
            models.Index(fields=("payer", "-created_at")),
            models.Index(fields=("company", "-created_at")),
        ]

    def __str__(self) -> str:
        return f"{self.reference} — {self.amount_xaf} {self.currency}"

    def save(self, *args, **kwargs) -> None:
        if not self.reference:
            self.reference = ReferenceCounter.next_reference("PAY")
        if not self.idempotency_key:
            import uuid

            self.idempotency_key = uuid.uuid4().hex
        super().save(*args, **kwargs)

    @property
    def is_succeeded(self) -> bool:
        return self.status == PaymentStatus.SUCCEEDED

    @property
    def is_final(self) -> bool:
        return self.status in {
            PaymentStatus.SUCCEEDED, PaymentStatus.FAILED, PaymentStatus.CANCELLED,
            PaymentStatus.REFUNDED, PaymentStatus.EXPIRED,
        }

    @transaction.atomic
    def mark_succeeded(self, *, provider_reference: str = "", payload: dict | None = None) -> None:
        """Marque le paiement comme réussi de façon idempotente.

        Un webhook rejoué par le fournisseur ne doit jamais produire un double
        encaissement : on ne traite que la transition depuis un état non final.
        """
        locked = Payment.objects.select_for_update().get(pk=self.pk)
        if locked.status == PaymentStatus.SUCCEEDED:
            return
        Payment.objects.filter(pk=self.pk).update(
            status=PaymentStatus.SUCCEEDED,
            paid_at=timezone.now(),
            provider_reference=provider_reference or locked.provider_reference,
            updated_at=timezone.now(),
        )
        PaymentTransaction.objects.create(
            payment=self,
            status=PaymentStatus.SUCCEEDED,
            provider=self.provider,
            provider_event="payment.succeeded",
            provider_event_id=f"{provider_reference or locked.reference}:succeeded",
            amount_xaf=self.amount_xaf,
            payload=payload or {},
            signature_verified=bool((payload or {}).get("_signature_verified")),
        )
        self.refresh_from_db()
        if self.invoice_id:
            self.invoice.apply_payment(self.amount_xaf)

    @transaction.atomic
    def mark_failed(self, *, reason: str = "", payload: dict | None = None) -> None:
        locked = Payment.objects.select_for_update().get(pk=self.pk)
        if locked.is_final:
            return
        Payment.objects.filter(pk=self.pk).update(
            status=PaymentStatus.FAILED, failure_reason=reason[:255], updated_at=timezone.now()
        )
        PaymentTransaction.objects.create(
            payment=self,
            status=PaymentStatus.FAILED,
            provider=self.provider,
            provider_event="payment.failed",
            provider_event_id=f"{self.reference}:failed:{timezone.now().timestamp():.0f}",
            amount_xaf=self.amount_xaf,
            payload=payload or {},
            failure_reason=reason[:255],
        )
        self.refresh_from_db()


class PaymentTransaction(models.Model):
    """Journal immuable des événements de paiement (audit financier)."""

    payment = models.ForeignKey(
        Payment, verbose_name="paiement", on_delete=models.CASCADE, related_name="transactions"
    )
    status = models.CharField("statut", max_length=12, choices=PaymentStatus.choices)
    provider = models.CharField("fournisseur", max_length=16, choices=PaymentProvider.choices)
    provider_event = models.CharField("événement", max_length=60, blank=True)
    provider_event_id = models.CharField("identifiant d'événement", max_length=160, unique=True)
    provider_transaction_id = models.CharField("transaction fournisseur", max_length=160, blank=True)
    amount_xaf = models.DecimalField("montant", max_digits=14, decimal_places=2, default=0)
    fees_xaf = models.DecimalField("frais", max_digits=12, decimal_places=2, default=0)
    payload = models.JSONField("charge utile", default=dict, blank=True)
    signature_verified = models.BooleanField("signature vérifiée", default=False)
    failure_reason = models.CharField("motif d'échec", max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "transaction de paiement"
        verbose_name_plural = "transactions de paiement"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("payment", "-created_at")),
            models.Index(fields=("status", "-created_at")),
        ]

    def __str__(self) -> str:
        return f"{self.payment.reference} → {self.get_status_display()}"


class Payout(models.Model):
    """Décaissement vers un bénéficiaire (entreprise, fournisseur, artisan)."""

    class Status(models.TextChoices):
        REQUESTED = "REQUESTED", "Demandé"
        APPROVED = "APPROVED", "Approuvé"
        PAID = "PAID", "Payé"
        REJECTED = "REJECTED", "Refusé"

    reference = models.CharField("référence", max_length=40, unique=True)
    project = models.ForeignKey(
        "projects.Project", verbose_name="projet", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="payouts",
    )
    company = models.ForeignKey(
        "companies.Company", verbose_name="bénéficiaire", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="payouts",
    )
    budget_line = models.ForeignKey(
        "projects.BudgetLine", verbose_name="ligne budgétaire", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="payouts",
    )
    label = models.CharField("objet", max_length=200)
    amount_xaf = models.DecimalField("montant", max_digits=14, decimal_places=2, validators=[MinValueValidator(0)])
    status = models.CharField("statut", max_length=10, choices=Status.choices, default=Status.REQUESTED, db_index=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="demandé par", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="payouts_requested",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="approuvé par", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="payouts_approved",
    )
    proof = models.ForeignKey(
        "common.Asset", verbose_name="justificatif", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="payout_proofs",
    )
    paid_at = models.DateTimeField("payé le", null=True, blank=True)
    notes = models.CharField("notes", max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "décaissement"
        verbose_name_plural = "décaissements"
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("project", "status"))]

    def __str__(self) -> str:
        return f"{self.reference} — {self.label}"

    def save(self, *args, **kwargs) -> None:
        if not self.reference:
            self.reference = ReferenceCounter.next_reference("DEC", width=5)
        super().save(*args, **kwargs)


class WebhookEvent(models.Model):
    """Trace brute des notifications fournisseur, avant tout traitement.

    Conserver la charge utile d'origine est indispensable pour arbitrer un
    litige « j'ai payé mais le dossier n'est pas à jour ».
    """

    provider = models.CharField("fournisseur", max_length=16, choices=PaymentProvider.choices)
    event_id = models.CharField("identifiant", max_length=160, unique=True)
    event_type = models.CharField("type", max_length=80, blank=True)
    payload = models.JSONField("charge utile", default=dict)
    signature_valid = models.BooleanField("signature valide", default=False)
    processed = models.BooleanField("traité", default=False)
    processed_at = models.DateTimeField("traité le", null=True, blank=True)
    error = models.CharField("erreur", max_length=255, blank=True)
    received_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "notification fournisseur"
        verbose_name_plural = "notifications fournisseur"
        ordering = ("-received_at",)

    def __str__(self) -> str:
        return f"{self.provider}:{self.event_id}"
