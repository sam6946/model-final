"""Profils clients : propriétaires locaux, investisseurs, diaspora, institutions.

Le modèle ``User`` porte l'identité et l'authentification ; ce profil porte le
contexte commercial, nécessaire pour qualifier une demande (pays de résidence,
fuseau, contacts terrain, préférences de communication).
"""
from __future__ import annotations

from django.conf import settings
from django.db import models

from common.constants import Country


class CustomerType(models.TextChoices):
    OWNER_LOCAL = "OWNER_LOCAL", "Propriétaire résidant au Cameroun"
    DIASPORA = "DIASPORA", "Propriétaire de la diaspora"
    INVESTOR = "INVESTOR", "Investisseur"
    INSTITUTION = "INSTITUTION", "Institution / entreprise cliente"
    FAMILY_PROXY = "FAMILY_PROXY", "Représentant familial"


class CustomerProfile(models.Model):
    """Contexte client complétant le compte utilisateur."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, verbose_name="utilisateur", on_delete=models.CASCADE,
        related_name="customer_profile",
    )
    customer_type = models.CharField(
        "type de client", max_length=20, choices=CustomerType.choices,
        default=CustomerType.OWNER_LOCAL, db_index=True,
    )
    country_of_residence = models.CharField(
        "pays de résidence", max_length=2, choices=Country.choices, default=Country.CM
    )
    city_of_residence = models.CharField("ville de résidence", max_length=120, blank=True)
    whatsapp = models.CharField("WhatsApp", max_length=24, blank=True)
    timezone_name = models.CharField("fuseau horaire", max_length=64, default="Africa/Douala")
    preferred_contact = models.CharField(
        "canal de contact préféré", max_length=20,
        choices=[("WHATSAPP", "WhatsApp"), ("SMS", "SMS"), ("EMAIL", "E-mail"), ("PHONE", "Appel")],
        default="WHATSAPP",
    )
    occupation = models.CharField("profession", max_length=120, blank=True)
    notes = models.TextField("notes internes KEMTA", blank=True)
    onboarded_at = models.DateTimeField("accompagné depuis", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "profil client"
        verbose_name_plural = "profils clients"
        indexes = [
            models.Index(fields=("customer_type",)),
            models.Index(fields=("country_of_residence",)),
        ]

    def __str__(self) -> str:
        return f"{self.user.full_name} — {self.get_customer_type_display()}"

    @property
    def is_diaspora(self) -> bool:
        return self.customer_type == CustomerType.DIASPORA or self.country_of_residence != "CM"


class Beneficiary(models.Model):
    """Contact terrain autorisé : famille, gardien, gestionnaire de confiance.

    Indispensable pour la diaspora : KEMTA doit pouvoir joindre quelqu'un sur
    place (remise de clés, accès au terrain) sans dépendre du client à l'étranger.
    """

    class Relation(models.TextChoices):
        FAMILY = "FAMILY", "Famille"
        GUARDIAN = "GUARDIAN", "Gardien"
        LOCAL_MANAGER = "LOCAL_MANAGER", "Gestionnaire local"
        LAWYER = "LAWYER", "Notaire / avocat"
        OTHER = "OTHER", "Autre"

    customer = models.ForeignKey(
        CustomerProfile, verbose_name="client", on_delete=models.CASCADE, related_name="beneficiaries"
    )
    full_name = models.CharField("nom complet", max_length=160)
    phone = models.CharField("téléphone", max_length=20)
    relation = models.CharField("lien", max_length=20, choices=Relation.choices, default=Relation.FAMILY)
    city = models.CharField("ville", max_length=120, blank=True)
    can_receive_keys = models.BooleanField("peut réceptionner les clés", default=False)
    can_authorize_work = models.BooleanField("peut autoriser des travaux", default=False)
    is_primary = models.BooleanField("contact principal", default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "contact terrain"
        verbose_name_plural = "contacts terrain"
        ordering = ("-is_primary", "full_name")
        constraints = [
            models.UniqueConstraint(
                fields=("customer", "phone"), name="uniq_beneficiary_phone_per_customer"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.full_name} ({self.get_relation_display()})"
