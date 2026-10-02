"""Valeurs écrites dans un document généré (issue #143) : fonctions pures, jamais de LLM.

Seules les valeurs **validées** du brouillon sont utilisées : une valeur seulement proposée n'entre pas dans le
document. Un champ obligatoire non validé n'est écrit qu'après confirmation explicite, avec la mention
« non renseigné », pour que le trou se voie dans le document."""

import re
from datetime import datetime
from typing import Any

from app.models.document_draft import DocumentFieldVersion, FieldStatus
from app.schemas.document_template import FieldDefinition, MetadataSource

NOT_FILLED = "[non renseigné]"
_ISO_DAY = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")


def format_date(value: str) -> str:
    """Une date ISO (AAAA-MM-JJ) s'écrit JJ/MM/AAAA ; tout autre texte est laissé tel quel."""
    match = _ISO_DAY.match(value.strip())
    return f"{match.group(3)}/{match.group(2)}/{match.group(1)}" if match else value


def format_value(definition: FieldDefinition, value: Any) -> Any:
    """Valeur d'un champ validé, mise en forme pour le document : texte, ou liste de textes."""
    match definition.type:
        case "list":
            return [str(item) for item in value]
        case "boolean":
            return "oui" if value else "non"
        case "number":
            return str(value).replace(".", ",")
        case "date":
            return format_date(str(value))
        case _:
            return str(value)


def _empty(definition: FieldDefinition, *, mark: bool) -> Any:
    if definition.type == "list":
        return [NOT_FILLED] if mark else []
    return NOT_FILLED if mark else ""


def build_values(
    definitions: list[FieldDefinition],
    current: dict[str, DocumentFieldVersion],
    *,
    generated_at: datetime,
    document_version: int,
) -> tuple[dict[str, Any], list[str]]:
    """(valeurs par nom de champ, champs obligatoires non validés). Un champ facultatif non validé est vide."""
    values: dict[str, Any] = {}
    incomplete: list[str] = []
    for definition in definitions:
        source = definition.source
        if isinstance(source, MetadataSource) and source.key == "generated_at":
            values[definition.name] = format_value(definition, generated_at.date().isoformat())
        elif isinstance(source, MetadataSource) and source.key == "document_version":
            values[definition.name] = str(document_version)
        elif current[definition.name].status == FieldStatus.VALIDE and current[definition.name].value is not None:
            values[definition.name] = format_value(definition, current[definition.name].value)
        elif definition.required:
            incomplete.append(definition.name)
            values[definition.name] = _empty(definition, mark=True)
        else:
            values[definition.name] = _empty(definition, mark=False)
    return values, incomplete
