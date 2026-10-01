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
