"""Règles pures des colonnes personnalisées (issue #173) : validation des valeurs, défauts, filtres."""

import json
from decimal import Decimal

import pytest

from app.services.custom_fields import (
    FieldFilterError,
    current_values,
    default_values,
    normalize_value,
    parse_field_filters,
    validate_value,
)


def field(type_: str, **extra) -> dict:
    return {"id": "f_test1", "name": "Champ", "type": type_, "required": False, "choices": [], **extra}


# --- Validation, mêmes messages que l'interface ---


@pytest.mark.parametrize(
    ("type_", "value", "expected"),
    [
        ("text", "bonjour", None),
        ("text", 12, "Saisissez du texte."),
        ("text", "x" * 1001, "Le texte est limité à 1000 caractères."),
        ("number", 12, None),
        ("number", -3.5, None),
        ("number", "12", "Saisissez un nombre."),
        ("number", True, "Saisissez un nombre."),  # un oui/non n'est pas un nombre
        ("number", float("inf"), "Saisissez un nombre."),
        ("number", 1e16, "Saisissez un nombre."),
        ("amount", 0, None),
        ("amount", 1234.5, None),
        ("amount", -1, "Saisissez un montant positif."),
        ("amount", "10", "Saisissez un montant positif."),
        ("date", "2026-10-08", None),
        ("date", "2026-02-30", "Saisissez une date valide."),
        ("date", "08/10/2026", "Saisissez une date valide."),
        ("date", 20261008, "Saisissez une date valide."),
        ("boolean", True, None),
        ("boolean", False, None),
        ("boolean", "oui", "Valeur invalide."),
        ("boolean", 1, "Valeur invalide."),
    ],
)
def test_validate_value(type_: str, value, expected) -> None:
    assert validate_value(field(type_), value) == expected


def test_choice_must_belong_to_the_list() -> None:
    choice = field("choice", choices=["Culture", "Sport"])

    assert validate_value(choice, "Sport") is None
    assert validate_value(choice, "Social") == "Choisissez une valeur de la liste."
    assert validate_value(choice, 3) == "Choisissez une valeur de la liste."


@pytest.mark.parametrize("empty", [None, ""])
def test_an_empty_value_is_allowed_unless_the_field_is_required(empty) -> None:
    assert validate_value(field("text"), empty) is None
    assert validate_value(field("text", required=True), empty) == "Ce champ est obligatoire."
    assert validate_value(field("amount", required=True), empty) == "Ce champ est obligatoire."
    # Un oui/non n'est jamais « vide » : « Non » est une réponse.
    assert validate_value(field("boolean", required=True), empty) is None


def test_normalize_value_turns_empty_into_none() -> None:
    assert normalize_value("") is None and normalize_value(None) is None
    assert normalize_value(0) == 0 and normalize_value(False) is False and normalize_value("a") == "a"


# --- Défauts et valeurs courantes ---


def test_default_values_keep_the_defaults_that_exist() -> None:
    fields = [
        {"id": "f_aaaa", "default_value": "Culture"},
        {"id": "f_bbbb", "default_value": None},
        {"id": "f_cccc", "default_value": False},  # « Non » est un défaut valable
        {"id": "f_dddd", "default_value": 0},
    ]

    assert default_values(fields) == {"f_aaaa": "Culture", "f_cccc": False, "f_dddd": 0}


def test_current_values_drop_deleted_fields() -> None:
    fields = [{"id": "f_aaaa"}]

    assert current_values(fields, {"f_aaaa": 1, "f_gone": 2}) == {"f_aaaa": 1}
    assert current_values(fields, None) == {}


# --- Filtres ---


def _fields() -> list[dict]:
    return [
        field("text", id="f_text", name="Texte"),
        field("number", id="f_nombre", name="Nombre"),
        field("amount", id="f_montant", name="Montant"),
        field("date", id="f_date", name="Date"),
        field("boolean", id="f_bool", name="Oui/non"),
        field("choice", id="f_choix", name="Choix", choices=["a"]),
    ]


def test_parse_field_filters_by_type() -> None:
    raw = json.dumps(
        {
            "f_text": "abc",
            "f_nombre": {"min": "1,5", "max": "10"},
            "f_date": {"min": "2026-01-01", "max": ""},
            "f_bool": "true",
            "f_choix": "a",
        }
    )

    parsed = {f.field["id"]: f for f in parse_field_filters(raw, _fields())}

    assert parsed["f_text"].text == "abc"
    assert (parsed["f_nombre"].minimum, parsed["f_nombre"].maximum) == (Decimal("1.5"), Decimal("10"))
    assert (parsed["f_date"].minimum, parsed["f_date"].maximum) == ("2026-01-01", None)
    assert parsed["f_bool"].text == "true" and parsed["f_choix"].text == "a"


def test_empty_filters_are_ignored() -> None:
    raw = json.dumps({"f_text": "", "f_nombre": {"min": "", "max": ""}, "f_bool": ""})

    assert parse_field_filters(raw, _fields()) == []
    assert parse_field_filters(None, _fields()) == []
    assert parse_field_filters("", _fields()) == []


@pytest.mark.parametrize(
    "raw",
    [
        "pas du json",
        "[1, 2]",
        json.dumps({"f_inconnu": "x"}),  # champ qui n'est pas de l'analyse
        json.dumps({"f_nombre": "5"}),  # un nombre attend un intervalle
        json.dumps({"f_nombre": {"min": "abc"}}),
        json.dumps({"f_nombre": {"min": "NaN"}}),
        json.dumps({"f_nombre": {"min": "10", "max": "2"}}),
        json.dumps({"f_date": {"min": "demain"}}),
        json.dumps({"f_bool": "peut-être"}),
        json.dumps({"f_text": 5}),
        json.dumps({"f_text": "x" * 201}),
        "{" + '"f_text": "a",' * 400 + '"f_nombre": 1}',  # trop long
    ],
)
def test_invalid_filters_are_refused(raw: str) -> None:
    with pytest.raises(FieldFilterError):
        parse_field_filters(raw, _fields())
