"""Schémas des brouillons de document (issue #140). Internes : jamais exposés côté usager (#96)."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DraftCreateIn(BaseModel):
    template_id: uuid.UUID
    # Révision de l'analyse à utiliser ; à défaut, un instantané de l'analyse courante est pris.
    revision_id: uuid.UUID | None = None


class FieldValueIn(BaseModel):
    """Valeur saisie par l'instructeur : elle est validée d'office (saisie à la main)."""

    value: Any
    reason: str | None = Field(default=None, max_length=2000)


class FieldRejectIn(BaseModel):
    reason: str | None = Field(default=None, max_length=2000)


class FieldRestoreIn(BaseModel):
    version_id: uuid.UUID


class FieldsValidateIn(BaseModel):
    """Valide d'un coup des valeurs proposées ; sans liste, toutes celles qui le sont."""

    names: list[str] | None = None


class FieldVersionOut(BaseModel):
    id: uuid.UUID
    field_name: str
    version_number: int
    value: Any | None
    status: str
    origin: str
    sources: list[dict[str, Any]]
    author_id: str | None
    reason: str | None
    restored_from_version_id: uuid.UUID | None
    prompt_version: str | None
    model: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DraftFieldOut(BaseModel):
    """Un champ du modèle avec son état courant."""

    name: str
    label: str
    type: str
    required: bool
    instruction: str
    source: dict[str, Any]
    current: FieldVersionOut


class CompletenessOut(BaseModel):
    complete: bool
    # Champs obligatoires qui ne sont pas encore validés : à renseigner, ou seulement proposés.
    missing: list[str]
    proposed: list[str]


class DraftOut(BaseModel):
    id: uuid.UUID
    dossier_id: uuid.UUID
    analysis_id: uuid.UUID
    revision_id: uuid.UUID
    template_id: uuid.UUID
    template_version_id: uuid.UUID
    template_name: str
    template_version_number: int
    status: str
    created_by: str
    created_at: datetime
    fields: list[DraftFieldOut]
    completeness: CompletenessOut
    # Génération des valeurs par l'agent (#141).
    generation_status: str | None = None
    generation_requested_at: datetime | None = None
    generation_error: str | None = None
    generation_proposal_count: int | None = None
    generation_missing: list[str] | None = None
    generation_truncated: bool = False
    generation_prompt_version: str | None = None


class DraftSummaryOut(BaseModel):
    id: uuid.UUID
    dossier_id: uuid.UUID
    template_id: uuid.UUID
    template_name: str
    template_version_number: int
    status: str
    created_by: str
    created_at: datetime


class FieldEventOut(BaseModel):
    id: uuid.UUID
    field_name: str
    kind: str
    version_id: uuid.UUID | None
    author_id: str | None
    duration_seconds: float | None
    prompt_version: str | None
    model: str | None
    sources: list[dict[str, Any]]
    detail: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Génération par l'agent (#141) ---


class GenerateIn(BaseModel):
    """Champs à générer ; sans liste, tous ceux qui ne sont pas validés."""

    names: list[str] | None = None


class RegenerateIn(BaseModel):
    """Consigne facultative de l'instructeur pour cette régénération (« plus court », « ton neutre »)."""

    instruction: str | None = Field(default=None, max_length=2000)


class PromptVersionOut(BaseModel):
    id: uuid.UUID
    version_number: int
    content: str
    author_id: str
    restored_from_version_id: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PromptCurrentOut(BaseModel):
    """Prompt en vigueur ; ``version_number`` est vide tant que le prompt par défaut s'applique."""

    version_number: int | None
    label: str
    content: str
    is_default: bool


class PromptCreateIn(BaseModel):
    content: str = Field(min_length=20, max_length=20000)


class PromptRestoreIn(BaseModel):
    version_id: uuid.UUID


class InternalFieldOut(BaseModel):
    name: str
    label: str
    type: str
    required: bool
    instruction: str
    source: dict[str, Any]
    status: str
    value: Any | None
    origin: str


class InternalElementOut(BaseModel):
    id: uuid.UUID
    version_id: uuid.UUID
    kind: str
    name: str | None
    text: str
    page: int | None
    document_id: uuid.UUID | None


class InternalDraftNoteOut(BaseModel):
    id: uuid.UUID
    version_number: int
    content: str


class InternalDraftContextOut(BaseModel):
    """Tout ce dont le worker a besoin pour générer : définition des champs, éléments de la révision figée,
    notes internes, métadonnées du dossier et prompt en vigueur."""

    draft_id: uuid.UUID
    dossier_id: uuid.UUID
    status: str
    requested_by: str | None
    template_name: str
    generation_instructions: str
    fields: list[InternalFieldOut]
    elements: list[InternalElementOut]
    notes: list[InternalDraftNoteOut]
    metadata: dict[str, str | None]
    prompt_version_number: int | None
    prompt_label: str
    prompt: str


class InternalProposeIn(BaseModel):
    value: Any
    sources: list[dict[str, Any]] = Field(default_factory=list)
    prompt_version: str | None = None
    model: str | None = None
    instruction: str | None = None


class InternalGenerationIn(BaseModel):
    status: str = Field(pattern="^(terminé|échec)$")
    proposal_count: int | None = Field(default=None, ge=0)
    missing: list[str] = Field(default_factory=list)
    truncated: bool = False
    prompt_version: str | None = None
    error: str | None = Field(default=None, max_length=2000)
