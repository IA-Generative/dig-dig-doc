"""Schémas des propositions de modification de l'analyse de dossier (#114)."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.analysis_proposal import ProposalEventKind, ProposalStatus
from app.models.dossier_analysis import AnalysisElementKind
from app.schemas.dossier_analysis import VersionSource


class ProposalCreateIn(BaseModel):
    """Propose de modifier un élément existant (``element_id``) ou d'en créer
    un (``kind``) - l'un ou l'autre, jamais les deux."""

    element_id: uuid.UUID | None = None
    kind: AnalysisElementKind | None = None
    definition_name: str | None = Field(default=None, max_length=200)
    value: dict[str, Any]
    reason: str = Field(min_length=1, max_length=2000)
    source_type: VersionSource | None = None
    source_id: uuid.UUID | None = None
    # Contexte de génération (quand la proposition vient d'un agent).
    model: str | None = Field(default=None, max_length=200)
    prompt_version: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def _element_or_kind(self) -> "ProposalCreateIn":
        if (self.element_id is None) == (self.kind is None):
            raise ValueError("Indiquer soit element_id (modifier un élément), soit kind (en créer un)")
        return self


class ProposalModifyIn(BaseModel):
    """Accepter avec une autre valeur que celle proposée."""

    value: dict[str, Any]
    reason: str | None = Field(default=None, max_length=2000)


class ProposalRejectIn(BaseModel):
    reason: str | None = Field(default=None, max_length=2000)


class ProposalEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    proposal_id: uuid.UUID
    kind: ProposalEventKind
    actor_id: str
    value: dict[str, Any]
    note: str | None
    duration_seconds: float | None
    model: str | None
    prompt_version: str | None
    created_at: datetime


class ProposalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    analysis_id: uuid.UUID
    element_id: uuid.UUID | None
    kind: AnalysisElementKind
    definition_name: str | None
    base_version_id: uuid.UUID | None
    proposed_value: dict[str, Any]
    reason: str
    source_type: str | None
    source_id: uuid.UUID | None
    proposed_by: str
    model: str | None
    prompt_version: str | None
    status: ProposalStatus
    decided_by: str | None
    decided_at: datetime | None
    resulting_version_id: uuid.UUID | None
    resulting_element_id: uuid.UUID | None
    created_at: datetime


class ProposalDetailOut(ProposalOut):
    events: list[ProposalEventOut]
