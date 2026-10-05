"""Constantes partagées par toute la plateforme KEMTA."""
from __future__ import annotations

from django.db import models


class Country(models.TextChoices):
    CM = "CM", "Cameroun"
    FR = "FR", "France"
    BE = "BE", "Belgique"
    US = "US", "États-Unis"
    CA = "CA", "Canada"
    GB = "GB", "Royaume-Uni"
    DE = "DE", "Allemagne"
    CH = "CH", "Suisse"
    GA = "GA", "Gabon"
    CI = "CI", "Côte d'Ivoire"
    SN = "SN", "Sénégal"
    NG = "NG", "Nigeria"
    GQ = "GQ", "Guinée équatoriale"
    TD = "TD", "Tchad"
    OTHER = "OT", "Autre"


class Currency(models.TextChoices):
    XAF = "XAF", "Franc CFA (XAF)"
    EUR = "EUR", "Euro"
    USD = "USD", "Dollar américain"


CAMEROON_REGIONS = [
    ("AD", "Adamaoua"),
    ("CE", "Centre"),
    ("ES", "Est"),
    ("EN", "Extrême-Nord"),
    ("LT", "Littoral"),
    ("NO", "Nord"),
    ("NW", "Nord-Ouest"),
    ("OU", "Ouest"),
    ("SU", "Sud"),
    ("SW", "Sud-Ouest"),
]


class LocationKind(models.TextChoices):
    REGION = "REGION", "Région"
    CITY = "CITY", "Ville"
    NEIGHBOURHOOD = "NEIGHBOURHOOD", "Quartier"
    DIASPORA_CITY = "DIASPORA_CITY", "Ville de la diaspora"


class AssetKind(models.TextChoices):
    IMAGE = "IMAGE", "Image"
    VIDEO = "VIDEO", "Vidéo"
    DOCUMENT = "DOCUMENT", "Document"


class AssetStatus(models.TextChoices):
    PENDING = "PENDING", "En attente"
    READY = "READY", "Prêt"
    FAILED = "FAILED", "Échec"


class UploadKind(models.TextChoices):
    EVIDENCE_PHOTO = "EVIDENCE_PHOTO", "Photo de chantier"
    PROPERTY_PHOTO = "PROPERTY_PHOTO", "Photo de propriété"
    REALIZATION_PHOTO = "REALIZATION_PHOTO", "Photo de réalisation"
    COMPANY_LOGO = "COMPANY_LOGO", "Logo entreprise"
    COMPANY_COVER = "COMPANY_COVER", "Bannière entreprise"
    PROJECT_COVER = "PROJECT_COVER", "Couverture projet"
    USER_AVATAR = "USER_AVATAR", "Avatar utilisateur"
    PLAN = "PLAN", "Plan / devis"
    DOCUMENT = "DOCUMENT", "Document administratif"
    REPORT = "REPORT", "Rapport généré"


class NotificationType(models.TextChoices):
    SERVICE_REQUEST = "SERVICE_REQUEST", "Demande de service"
    PROJECT = "PROJECT", "Projet"
    TASK = "TASK", "Tâche"
    EVIDENCE = "EVIDENCE", "Preuve terrain"
    REPORT = "REPORT", "Rapport"
    PAYMENT = "PAYMENT", "Paiement"
    SUBSCRIPTION = "SUBSCRIPTION", "Abonnement"
    APPLICATION = "APPLICATION", "Candidature"
    COMPANY = "COMPANY", "Entreprise"
    OPPORTUNITY = "OPPORTUNITY", "Opportunité"
    MAINTENANCE = "MAINTENANCE", "Entretien"
    SECURITY = "SECURITY", "Sécurité"
    SYSTEM = "SYSTEM", "Système"


class NotificationChannel(models.TextChoices):
    IN_APP = "IN_APP", "Application"
    SMS = "SMS", "SMS"
    EMAIL = "EMAIL", "E-mail"
    WHATSAPP = "WHATSAPP", "WhatsApp"


class NotificationStatus(models.TextChoices):
    PENDING = "PENDING", "En attente"
    SENT = "SENT", "Envoyée"
    FAILED = "FAILED", "Échec"
    READ = "READ", "Lue"


class Level(models.TextChoices):
    INFO = "INFO", "Information"
    SUCCESS = "SUCCESS", "Succès"
    WARNING = "WARNING", "Attention"
    ERROR = "ERROR", "Erreur"


class Visibility(models.TextChoices):
    INTERNAL = "INTERNAL", "Interne"
    CUSTOMER = "CUSTOMER", "Client"
    PUBLIC = "PUBLIC", "Public"
