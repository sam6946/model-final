"""Utilitaires transverses : téléphone, références, slugs, montants."""
from __future__ import annotations

import re
import secrets
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.utils import timezone
from django.utils.text import slugify as django_slugify

# Indicatifs par défaut pour les formats locaux saisis par nos utilisateurs.
DEFAULT_CALLING_CODE = "237"
COUNTRY_CALLING_CODES = {
    "CM": "237",
    "FR": "33",
    "BE": "32",
    "CH": "41",
    "CA": "1",
    "US": "1",
    "GB": "44",
    "DE": "49",
    "GA": "241",
    "CI": "225",
    "SN": "221",
    "NG": "234",
    "GQ": "240",
    "TD": "235",
}

# Longueurs nationales significatives (numéro court, hors indicatif) par pays.
NATIONAL_NUMBER_LENGTHS = {
    "CM": (9,),  # 6 XX XX XX XX
    "FR": (9,),
    "BE": (8, 9),
    "CH": (9,),
    "CA": (10,),
    "US": (10,),
    "GB": (10,),
    "DE": (10, 11),
    "GA": (7, 8),
    "CI": (10,),
    "SN": (9,),
    "NG": (10,),
    "GQ": (9,),
    "TD": (8,),
}

_WHATSAPP_INDICATORS = re.compile(r"^(00|\+)")


def normalize_phone(raw: str, default_country: str = "CM") -> str:
    """Normalise un numéro vers le format E.164 (`+237XXXXXXXXX`).

    Accepte les saisies locales (`6 99 12 34 56`, `0699123456`), les formats
    internationaux (`+33 6 12 ...`, `00336...`) et les numéros préfixés.
    Lève ``ValueError`` si le numéro ne peut pas être interprété.
    """
    if not raw:
        raise ValueError("Numéro de téléphone vide.")
    cleaned = _WHATSAPP_INDICATORS.sub("+", raw.strip())
    cleaned = re.sub(r"[^\d+]", "", cleaned)
    if not cleaned:
        raise ValueError("Numéro de téléphone invalide.")

    if cleaned.startswith("+"):
        digits = cleaned[1:]
        return _validate_e164("+" + digits, default_country)

    # Sans « + » : on devine via la longueur et les préfixes locaux.
    digits = re.sub(r"\D", "", cleaned)
    country_code = COUNTRY_CALLING_CODES.get(default_country, DEFAULT_CALLING_CODE)

    if digits.startswith("00"):
        return _validate_e164("+" + digits[2:], default_country)

    # Déjà préfixé par son indicatif international (237 699...).
    for code in sorted(set(COUNTRY_CALLING_CODES.values()), key=len, reverse=True):
        if digits.startswith(code) and len(digits) - len(code) >= 8:
            return _validate_e164("+" + digits, default_country)

    # Saisie locale : 6XXXXXXXX / 0XXXXXXXXX
    local = digits.lstrip("0") if digits.startswith("0") else digits
    return _validate_e164(f"+{country_code}{local}", default_country)


def _validate_e164(candidate: str, default_country: str) -> str:
    match = re.fullmatch(r"\+(\d{7,15})", candidate)
    if not match:
        raise ValueError("Format international invalide (E.164 attendu).")
    digits = match.group(1)
    national = digits[len(COUNTRY_CALLING_CODES.get(default_country, "")) :]
    expected = NATIONAL_NUMBER_LENGTHS.get(default_country)
    if digits.startswith(COUNTRY_CALLING_CODES.get(default_country, "x")) and expected:
        if len(national) not in expected:
            raise ValueError(
                f"Un numéro {default_country} doit contenir {expected[0]} chiffres "
                "après l'indicatif."
            )
    return candidate


def mask_phone(phone: str) -> str:
    """Masque un numéro pour les logs et les réponses publiques."""
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) <= 5:
        return "***"
    return f"{phone[:4]}{'*' * (len(digits) - 7)}{digits[-3:]}"


def format_phone_display(phone: str) -> str:
    """`+237699112233` -> `+237 6 99 11 22 33` (lisibilité côté interface)."""
    if not phone or not phone.startswith("+"):
        return phone
    for code in ("237", "241", "225", "221", "234", "240", "235"):
        if phone.startswith("+" + code):
            rest = phone[len(code) + 1 :]
            if len(rest) == 9:
                # Numérotation africaine courante : 6 99 11 22 33 (préfixe + 4 paires)
                groups = " ".join([rest[0]] + [rest[i : i + 2] for i in range(1, 9, 2)])
            elif len(rest) == 8:
                groups = " ".join(rest[i : i + 2] for i in range(0, 8, 2))
            else:
                groups = " ".join(rest[i : i + 2] for i in range(0, len(rest), 2))
            return f"+{code} {groups}"
    return phone


def slugify(value: str, max_length: int = 70) -> str:
    """Slug ASCII stable, tolérant aux accents et aux caractères non latins."""
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = django_slugify(ascii_value)[:max_length].strip("-")
    return slug or secrets.token_hex(4)


def build_reference(prefix: str, sequence: int, *, year: int | None = None, width: int = 6) -> str:
    """Construit une référence lisible, ex. ``KEMTA-REQ-2026-000124``."""
    current_year = year or timezone.localdate().year
    return f"KEMTA-{prefix}-{current_year}-{sequence:0{width}d}"


def parse_amount(value: str | int | float | Decimal | None) -> Decimal | None:
    """Convertit un montant saisi (texte, « 15 000 000 FCFA ») en Decimal."""
    if value is None or value == "":
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    cleaned = re.sub(r"[^\d,.\-]", "", str(value)).replace(",", ".")
    if cleaned.count(".") > 1:
        cleaned = cleaned.replace(".", "", cleaned.count(".") - 1)
    try:
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None


def humanize_amount(amount: Decimal | int | None, currency: str = "XAF") -> str:
    """`15000000 XAF` -> `15 000 000 FCFA` (affichage commercial)."""
    if amount is None:
        return "—"
    formatted = f"{int(amount):,}".replace(",", " ")
    label = {"XAF": "FCFA", "EUR": "€", "USD": "$"}.get(currency, currency)
    return f"{formatted} {label}".strip()


def today_or_none(value: str | None) -> date | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def percent(part: Decimal | float | None, total: Decimal | float | None) -> float:
    """Pourcentage borné 0–100, robuste aux divisions par zéro."""
    try:
        if not total:
            return 0.0
        ratio = float(part or 0) / float(total) * 100
    except (TypeError, ValueError, ZeroDivisionError):
        return 0.0
    return round(max(0.0, min(100.0, ratio)), 2)


def safe_int(value: object, default: int = 0) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def group_by(items, key):
    """Regroupe une liste en dict — utilisé par les endpoints agrégés."""
    result: dict = {}
    for item in items:
        result.setdefault(key(item), []).append(item)
    return result
