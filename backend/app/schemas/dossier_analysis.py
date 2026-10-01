"""Schémas de l'analyse de dossier (issue #112, parent #106).

La valeur d'une version est validée selon le type de l'élément : voir
``validate_element_value``. Tout est interne - aucun schéma n'est exposé à
l'usager (#96)."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.models.dossier_analysis import (
    AnalysisElementKind,
    AnalysisUnitKind,
    AnalysisUnitStatus,
    DossierAnalysisStatus,
    ElementVersionOrigin,
)

# --- Valeurs par type d'élément ---


class _Value(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ClassificationValue(_Value):
    label: str


class EntityValue(_Value):
    value: str


class RelationValue(_Value):
    """Relation entre deux éléments de la même analyse (par identifiant)."""

    type: str
    source_element_id: uuid.UUID
    target_element_id: uuid.UUID


class SynthesisValue(_Value):
    text: str


class FieldValue(_Value):
    value: str


_VALUE_MODELS: dict[AnalysisElementKind, type[_Value]] = {
    AnalysisElementKind.CLASSIFICATION: ClassificationValue,
    AnalysisElementKind.ENTITY: EntityValue,
    AnalysisElementKind.RELATION: RelationValue,
    AnalysisElementKind.SYNTHESIS: SynthesisValue,
    AnalysisElementKind.FIELD: FieldValue,
}


class InvalidElementValueError(ValueError):
    pass


def validate_element_value(kind: AnalysisElementKind, value: dict[str, Any]) -> dict[str, Any]:
    """Valide la valeur d'une version pour le type d'élément et la renvoie
    sous forme JSON (les identifiants sont sérialisés en texte)."""
    try:
        return _VALUE_MODELS[kind].model_validate(value).model_dump(mode="json")
    except ValidationError as error:
        raise InvalidElementValueError(f"Valeur invalide pour un élément « {kind.value} » : {error}") from error


# --- Sorties ---


class ElementVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    element_id: uuid.UUID
    version_number: int
    value: dict[str, Any]
    confidence: float | None
    origin: ElementVersionOrigin
    prediction_id: uuid.UUID | None
    author_id: str | None
    reason: str | None
    source_type: str | None
    source_id: uuid.UUID | None
    restored_from_version_id: uuid.UUID | None
    origin_version_id: uuid.UUID | None
    created_at: datetime


class AnalysisElementOut(BaseModel):
    """Un élément avec sa version retenue (qui fait foi) et la dernière
    version produite par le modèle (qui peut en différer)."""

    id: uuid.UUID
    analysis_id: uuid.UUID
    unit_id: uuid.UUID | None
    kind: AnalysisElementKind
    definition_id: uuid.UUID | None
    definition_name: str | None
    document_id: uuid.UUID | None
    first_page_number: int | None
    source_prediction_id: uuid.UUID | None
    origin_element_id: uuid.UUID | None
    needs_review: bool
    review_reason: str | None
    retained_version: ElementVersionOut | None
    latest_model_version: ElementVersionOut | None
    created_at: datetime


class AnalysisUnitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    analysis_id: uuid.UUID
    kind: AnalysisUnitKind
    description: dict[str, Any]
    status: AnalysisUnitStatus
    input_fingerprint: str | None
    element_count: int
    source_unit_id: uuid.UUID | None
    created_at: datetime


class DossierAnalysisSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dossier_id: uuid.UUID
    sequence: int
    status: DossierAnalysisStatus
    analyse_version: str | None
    model: str | None
    started_at: datetime | None
    ended_at: datetime | None
    previous_analysis_id: uuid.UUID | None
    created_at: datetime


class DossierAnalysisOut(DossierAnalysisSummaryOut):
    elements: list[AnalysisElementOut]


class RestoreVersionIn(BaseModel):
    version_id: uuid.UUID
    reason: str | None = Field(default=None, max_length=2000)


class RevisionIn(BaseModel):
    label: str | None = Field(default=None, max_length=200)


class RevisionItemOut(BaseModel):
    element_id: uuid.UUID
    version_id: uuid.UUID


class AnalysisRevisionSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    analysis_id: uuid.UUID
    number: int
    label: str | None
    author_id: str | None
    created_at: datetime


class AnalysisRevisionOut(AnalysisRevisionSummaryOut):
    items: list[RevisionItemOut]
