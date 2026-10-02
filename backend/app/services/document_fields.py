"""Valeurs des champs d'un brouillon de document (issue #140) : typage et valeurs de départ.

Les valeurs de départ viennent de l'analyse (révision figée du brouillon), de métadonnées du dossier
ou de l'instructeur ; les autres champs restent « non renseigné » jusqu'à la proposition de l'agent (#141)
ou la saisie d'un instructeur."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.factory import RequestContext
from app.models.document_draft import FieldOrigin, FieldStatus
from app.models.dossier import Dossier
from app.models.dossier_analysis import (
    AnalysisElement,
    AnalysisElementKind,
    AnalysisElementVersion,
    AnalysisRevision,
    AnalysisRevisionItem,
)
from app.schemas.document_template import AnalysisSource, FieldDefinition, InstructionSource, MetadataSource

_TRUE = {"oui", "true", "vrai", "1", "yes"}
_FALSE = {"non", "false", "faux", "0", "no"}


class FieldValueError(ValueError):
    """La valeur ne correspond pas au type du champ."""


def coerce_value(field_type: str, raw: Any) -> Any:
    """Valide une valeur saisie (instructeur, agent) pour le type du champ ; renvoie la valeur propre."""
    if field_type in ("text", "date"):
        if not isinstance(raw, str) or not raw.strip():
            raise FieldValueError("Une valeur texte non vide est attendue")
        return raw.strip()
    if field_type == "number":
        if isinstance(raw, bool):
            raise FieldValueError("Un nombre est attendu")
        if isinstance(raw, int | float):
            return raw
        if isinstance(raw, str):
            try:
                number = float(raw.strip().replace(",", ".").replace(" ", ""))
            except ValueError:
                raise FieldValueError("Un nombre est attendu") from None
            return int(number) if number.is_integer() else number
        raise FieldValueError("Un nombre est attendu")
    if field_type == "boolean":
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, str) and raw.strip().casefold() in _TRUE | _FALSE:
            return raw.strip().casefold() in _TRUE
        raise FieldValueError("Un booléen (oui/non) est attendu")
    if field_type == "list":
        if not isinstance(raw, list) or not raw or not all(isinstance(x, str) and x.strip() for x in raw):
            raise FieldValueError("Une liste non vide de textes est attendue")
        return [x.strip() for x in raw]
    raise FieldValueError(f"Type de champ inconnu : {field_type}")


def value_to_text(value: Any) -> str:
    """Texte d'une valeur, pour la recopier dans l'analyse (élément « field », valeur texte)."""
    if isinstance(value, bool):
        return "oui" if value else "non"
    if isinstance(value, list):
        return "\n".join(str(x) for x in value)
    return str(value)


def element_text(kind: AnalysisElementKind, value: dict[str, Any]) -> str:
    match kind:
        case AnalysisElementKind.CLASSIFICATION:
            return str(value.get("label", ""))
        case AnalysisElementKind.SYNTHESIS:
            return str(value.get("text", ""))
        case AnalysisElementKind.RELATION:
            return str(value.get("type", ""))
        case _:
            return str(value.get("value", ""))


@dataclass
class InitialValue:
    value: Any | None
    status: FieldStatus
    origin: FieldOrigin
    sources: list[dict[str, Any]] = field(default_factory=list)


def _lenient(field_type: str, texts: list[str]) -> Any:
    """Valeur tirée de l'analyse (toujours du texte) : typée si possible, sinon laissée en texte —
    c'est une proposition, la personne qui relit la corrige."""
    if field_type == "list":
        return texts
    try:
        return coerce_value(field_type, texts[0])
    except FieldValueError:
        return texts[0]


def _metadata(key: str, dossier: Dossier, user: RequestContext, revision_number: int | None) -> Any | None:
    def day(moment: datetime | None) -> str | None:
        return moment.date().isoformat() if moment else None

    match key:
        case "dossier_name":
            return dossier.name
        case "dossier_id":
            return str(dossier.id)
        case "dossier_created_at":
            return day(dossier.created_at)
        case "dossier_started_at":
            return day(dossier.started_at)
        case "dossier_ended_at":
            return day(dossier.ended_at)
        case "instructor_name":
            return " ".join(p for p in (user.first_name, user.last_name) if p) or user.email or user.user_id
        case "instructor_email":
            return user.email or None
        case "analysis_revision":
            return str(revision_number) if revision_number is not None else None
        case _:
            # « generated_at », « document_version » : posées à l'assemblage du fichier (#143).
            return None


@dataclass
class RevisionElement:
    """Un élément de l'analyse, tel que figé dans une révision (version retenue à ce moment-là)."""

    element: AnalysisElement
    version: AnalysisElementVersion
    text: str


async def load_revision_elements(db: AsyncSession, revision_id: uuid.UUID) -> list[RevisionElement]:
    """Éléments d'une révision, par page puis par date de création (ordre stable)."""
    rows = (
        await db.execute(
            select(AnalysisElement, AnalysisElementVersion)
            .join(AnalysisRevisionItem, AnalysisRevisionItem.element_id == AnalysisElement.id)
            .join(AnalysisElementVersion, AnalysisElementVersion.id == AnalysisRevisionItem.version_id)
            .where(AnalysisRevisionItem.revision_id == revision_id)
            .order_by(
                AnalysisElement.first_page_number.is_(None),
                AnalysisElement.first_page_number,
                AnalysisElement.created_at,
                AnalysisElement.id,
            )
        )
    ).all()
    text_of = {element.id: element_text(element.kind, version.value) for element, version in rows}
    result = []
    for element, version in rows:
        if element.kind == AnalysisElementKind.RELATION:
            source = text_of.get(uuid.UUID(version.value["source_element_id"]), "?")
            target = text_of.get(uuid.UUID(version.value["target_element_id"]), "?")
            text = f"{source} {version.value.get('type', '')} {target}".strip()
        else:
            text = text_of[element.id]
        result.append(RevisionElement(element, version, text))
    return result


async def resolve_initial_values(
    db: AsyncSession,
    *,
    dossier: Dossier,
    revision_id: uuid.UUID,
    fields: list[FieldDefinition],
    user: RequestContext,
) -> dict[str, InitialValue]:
    """Valeur de départ de chaque champ, tirée de la révision de l'analyse."""
    elements = await load_revision_elements(db, revision_id)
    revision = await db.get(AnalysisRevision, revision_id)

    def candidates(kind: AnalysisElementKind, name: str) -> list[RevisionElement]:
        return [
            e
            for e in elements
            if e.element.kind == kind
            and (e.element.definition_name or "").casefold() == name.casefold()
            and e.text.strip()
        ]

    def from_analysis(definition: FieldDefinition, kind: AnalysisElementKind, name: str) -> InitialValue:
        found = candidates(kind, name)
        if not found:
            return InitialValue(None, FieldStatus.NON_RENSEIGNE, FieldOrigin.ANALYSIS)
        # Un champ « liste » reprend toutes les occurrences ; les autres, la première (page la plus basse).
        used = found if definition.type == "list" else found[:1]
        return InitialValue(
            _lenient(definition.type, [e.text for e in used]),
            FieldStatus.PROPOSE,
            FieldOrigin.ANALYSIS,
            [
                {"type": "analysis_element", "element_id": str(e.element.id), "version_id": str(e.version.id)}
                for e in used
            ],
        )

    result: dict[str, InitialValue] = {}
    for definition in fields:
        source = definition.source
        if isinstance(source, AnalysisSource):
            result[definition.name] = from_analysis(
                definition, AnalysisElementKind(source.element_kind), source.definition_name
            )
        elif isinstance(source, InstructionSource):
            # Valeur déjà renseignée pour ce dossier (même nom) : reprise, à confirmer.
            result[definition.name] = from_analysis(definition, AnalysisElementKind.FIELD, definition.name)
        elif isinstance(source, MetadataSource):
            value = _metadata(source.key, dossier, user, revision.number if revision else None)
            result[definition.name] = InitialValue(
                value,
                FieldStatus.VALIDE if value is not None else FieldStatus.NON_RENSEIGNE,
                FieldOrigin.ANALYSIS,
                [{"type": "dossier_metadata", "key": source.key}],
            )
    return result
