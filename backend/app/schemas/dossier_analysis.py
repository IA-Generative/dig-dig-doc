"""Schémas de l'analyse de dossier (issue #112, parent #106).

La valeur d'une version est validée selon le type de l'élément : voir
``validate_element_value``. Tout est interne - aucun schéma n'est exposé à
l'usager (#96)."""

import uuid
from datetime import datetime
from typing import Any, Literal

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
    # Issue #120 : « validé », « corrigé » ou « rejeté » quand la version vient
    # d'une validation de prédiction ; zone corrigée éventuelle.
    validation_status: str | None
    bounding_box_id: uuid.UUID | None
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


# Source d'une modification d'instructeur : d'où vient l'information.
VersionSource = Literal["chat_message", "note", "proposal"]


class ElementCreateIn(BaseModel):
    """Élément ajouté à la main par un instructeur (y compris une relation)."""

    kind: AnalysisElementKind
    value: dict[str, Any]
    definition_name: str | None = Field(default=None, max_length=200)
    reason: str | None = Field(default=None, max_length=2000)
    source_type: VersionSource | None = None
    source_id: uuid.UUID | None = None


class ElementVersionCreateIn(BaseModel):
    """Nouvelle valeur apportée par un instructeur à un élément existant. Le
    motif est obligatoire : il fait partie de l'historique."""

    value: dict[str, Any]
    reason: str = Field(min_length=1, max_length=2000)
    source_type: VersionSource | None = None
    source_id: uuid.UUID | None = None
    # Version retenue que l'instructeur avait sous les yeux : si l'élément a changé
    # depuis, l'écriture est refusée (409) au lieu d'écraser le travail d'un autre.
    base_version_id: uuid.UUID | None = None


# --- API interne (worker) : unités de calcul ---


class AnalysisUnitCreateIn(BaseModel):
    kind: AnalysisUnitKind
    # Ce que couvre l'unité (page, lot de pages...) - forme libre.
    description: dict[str, Any] = Field(default_factory=dict)
    # Hash (sha256 hexadécimal) des entrées de l'unité, calculé par le worker :
    # sert à la relance incrémentale (#119).
    input_fingerprint: str | None = Field(default=None, min_length=64, max_length=64, pattern="^[0-9a-f]{64}$")


class ReusedEntity(BaseModel):
    name: str
    value: str


class AnalysisUnitRefOut(BaseModel):
    id: uuid.UUID
    analysis_id: uuid.UUID
    # Relance incrémentale (#119) : l'unité a été reprise de l'analyse précédente
    # (même empreinte), ses éléments sont déjà copiés, le worker ne la calcule pas.
    reused: bool = False
    # Entités reprises (valeurs produites par le modèle) : le worker en amorce la
    # fusion des doublons entre lots.
    reused_entities: list[ReusedEntity] = Field(default_factory=list)


class AgentReuseIn(BaseModel):
    step_id: uuid.UUID


class AgentReuseOut(BaseModel):
    reused: bool
    # Synthèse reprise, à déposer comme sortie de l'étape sans appeler le LLM.
    output: str | None = None


class AnalysisUnitCompleteIn(BaseModel):
    status: Literal["terminé", "échec"]
