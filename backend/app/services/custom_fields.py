"""Colonnes personnalisées du suivi (issue #173) : types, validation des valeurs, valeurs par défaut.

Logique **pure** : elle reproduit les règles de l'interface (`frontend/src/utils/trackingFields.ts`) pour que le serveur
refuse ce que l'interface refuse, avec les mêmes messages.

Types : ``text``, ``number``, ``amount`` (positif, avec une devise), ``date`` (``AAAA-MM-JJ``), ``boolean``, ``choice``
(valeur de la liste du champ). Une valeur vide (``null`` ou chaîne vide) est permise sauf si le champ est obligatoire
(un oui/non n'est jamais « vide »).
"""

import json
import math
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

FIELD_TYPES = ("text", "number", "amount", "date", "boolean", "choice")
CURRENCIES = ("EUR", "USD", "GBP")
# Bornes : un champ personnalisé reste une information de pilotage, pas un stockage de contenu.
MAX_FIELDS_PER_ANALYSE = 20
MAX_TEXT_LENGTH = 1000
MAX_NUMBER = 1e15

REQUIRED_MESSAGE = "Ce champ est obligatoire."


def is_empty(value: Any) -> bool:
    return value is None or value == ""


def _is_number(value: Any) -> bool:
    # `bool` est un `int` en Python : un oui/non n'est pas un nombre.
    return (
        isinstance(value, int | float)
        and not isinstance(value, bool)
        and math.isfinite(value)
        and abs(value) <= MAX_NUMBER
    )


def validate_value(field: dict[str, Any], value: Any) -> str | None:
    """Message d'erreur (en français) si la valeur ne convient pas au champ, sinon ``None``."""
    field_type = field["type"]
    if is_empty(value):
        return REQUIRED_MESSAGE if field.get("required") and field_type != "boolean" else None
    if field_type == "number":
        return None if _is_number(value) else "Saisissez un nombre."
    if field_type == "amount":
        return None if _is_number(value) and value >= 0 else "Saisissez un montant positif."
    if field_type == "date":
        if isinstance(value, str):
            try:
                date.fromisoformat(value)
                return None
            except ValueError:
                pass
        return "Saisissez une date valide."
    if field_type == "choice":
        return (
            None
            if isinstance(value, str) and value in field.get("choices", [])
            else "Choisissez une valeur de la liste."
        )
    if field_type == "boolean":
        return None if isinstance(value, bool) else "Valeur invalide."
    if not isinstance(value, str):
        return "Saisissez du texte."
    return None if len(value) <= MAX_TEXT_LENGTH else f"Le texte est limité à {MAX_TEXT_LENGTH} caractères."


def normalize_value(value: Any) -> Any:
    """Valeur à stocker : ``None`` pour une valeur vide."""
    return None if is_empty(value) else value


def default_values(fields: list[dict[str, Any]]) -> dict[str, Any]:
    """Valeurs données à un nouveau dossier : le défaut de chaque champ qui en a un."""
    return {field["id"]: field["default_value"] for field in fields if field.get("default_value") is not None}


def current_values(fields: list[dict[str, Any]], values: dict[str, Any] | None) -> dict[str, Any]:
    """Les valeurs d'un dossier pour les champs **actuels** de l'analyse : celles d'un champ supprimé (conservées en
    base, récupérables si le champ revient) n'en font pas partie."""
    wanted = {field["id"] for field in fields}
    return {key: value for key, value in (values or {}).items() if key in wanted}


# --- Filtres du suivi sur les colonnes personnalisées ---


class FieldFilterError(ValueError):
    """Un filtre de champ n'est pas valide (JSON mal formé, champ inconnu, valeur qui n'a pas le bon type)."""


@dataclass(frozen=True)
class FieldFilter:
    """Un filtre : ``text`` (texte contenu, choix égal, oui/non « true » ou « false ») ou une plage ``minimum`` et
    ``maximum`` pour un nombre, un montant ou une date (bornes incluses, l'une ou l'autre peut manquer)."""

    field: dict[str, Any]
    text: str | None = None
    minimum: Decimal | str | None = None
    maximum: Decimal | str | None = None


def _bound(field: dict[str, Any], raw: Any) -> Decimal | str | None:
    if raw in (None, ""):
        return None
    if not isinstance(raw, str):
        raise FieldFilterError(f"« {field['name']} » : borne invalide.")
    if field["type"] == "date":
        try:
            date.fromisoformat(raw)
        except ValueError as error:
            raise FieldFilterError(f"« {field['name']} » : date invalide.") from error
        return raw
    try:
        number = Decimal(raw.replace(",", "."))
    except InvalidOperation as error:
        raise FieldFilterError(f"« {field['name']} » : nombre invalide.") from error
    if not number.is_finite():
        raise FieldFilterError(f"« {field['name']} » : nombre invalide.")
    return number


def parse_field_filters(raw: str | None, fields: list[dict[str, Any]]) -> list[FieldFilter]:
    """Lit le paramètre ``field_filters`` du suivi : un objet JSON ``{identifiant du champ: filtre}``, où le filtre est
    un texte, ou ``{"min": …, "max": …}`` pour un nombre, un montant ou une date."""
    if not raw:
        return []
    if len(raw) > 4000:
        raise FieldFilterError("Les filtres de colonnes sont trop longs.")
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError as error:
        raise FieldFilterError("Les filtres de colonnes ne sont pas du JSON valide.") from error
    if not isinstance(decoded, dict):
        raise FieldFilterError("Les filtres de colonnes doivent être un objet.")
    by_id = {field["id"]: field for field in fields}
    parsed: list[FieldFilter] = []
    for field_id, spec in decoded.items():
        field = by_id.get(field_id)
        if field is None:
            raise FieldFilterError("Colonne inconnue pour cette analyse.")
        if field["type"] in ("number", "amount", "date"):
            if not isinstance(spec, dict):
                raise FieldFilterError(f"« {field['name']} » : un intervalle est attendu.")
            minimum, maximum = _bound(field, spec.get("min")), _bound(field, spec.get("max"))
            if minimum is not None and maximum is not None and minimum > maximum:
                raise FieldFilterError(f"« {field['name']} » : le minimum dépasse le maximum.")
            if minimum is not None or maximum is not None:
                parsed.append(FieldFilter(field, minimum=minimum, maximum=maximum))
        else:
            if not isinstance(spec, str) or len(spec) > 200:
                raise FieldFilterError(f"« {field['name']} » : un texte est attendu.")
            if field["type"] == "boolean" and spec not in ("", "true", "false"):
                raise FieldFilterError(f"« {field['name']} » : « true » ou « false » attendu.")
            if spec != "":
                parsed.append(FieldFilter(field, text=spec))
    return parsed
