"""Modèles de réponse, alignés sur backend/app/schemas/ (champs inconnus tolérés)."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class _Model(BaseModel):
    # Le backend peut ajouter des champs : le SDK ne doit pas casser dessus.
    model_config = ConfigDict(extra="allow")


class DossierStatus(StrEnum):
    EN_ATTENTE = "en_attente"
    EN_COURS = "en_cours"
    TERMINE = "terminé"
    ARRETE = "arrêté"
    ECHEC = "échec"

    @property
    def is_terminal(self) -> bool:
        return self in TERMINAL_STATUSES


TERMINAL_STATUSES = frozenset({DossierStatus.TERMINE, DossierStatus.ARRETE, DossierStatus.ECHEC})


class Page[T](_Model):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


class Version[T](_Model):
    id: uuid.UUID
    content: T
    created_at: datetime


class LabelDefinition(_Model):
    name: str
    definition: str = ""
    id: uuid.UUID | None = None


class EntityDefinition(_Model):
    name: str
    definition: str = ""
    # texte | date | nombre | booléen | identifiant
    type: str
    id: uuid.UUID | None = None


class Classification(_Model):
    prompt: str
    labels: list[LabelDefinition]
    prompt_versions: list[Version[str]] = []


class Extraction(_Model):
    prompt: str
    entities: list[EntityDefinition]
    prompt_versions: list[Version[str]] = []


class Agent(_Model):
    id: uuid.UUID
    name: str
    prompt: str
    tools: list[str]
    output: bool
    model: str | None = None


class AnalyseListItem(_Model):
    id: uuid.UUID
    name: str
    description: str
    created_at: datetime
    agent_count: int


class Analyse(_Model):
    id: uuid.UUID
    name: str
    description: str
    created_at: datetime
    classification: Classification
    extraction: Extraction
    agents: list[Agent]


class ExecutionLog(_Model):
    id: uuid.UUID
    level: str
    message: str
    created_at: datetime


class ExecutionStep(_Model):
    id: uuid.UUID
    kind: str
    label: str
    status: str
    started_at: datetime
    ended_at: datetime | None = None
    output: str | None = None
    logs: list[ExecutionLog] = []


class Prediction(_Model):
    id: uuid.UUID
    kind: str
    name: str
    value: str
    confidence: float | None = None


class Page_(_Model):
    """Page d'un document (nommée `Page_` pour ne pas masquer la pagination `Page`)."""

    id: uuid.UUID
    page_number: int
    content: str | None = None
    predictions: list[Prediction] = []


class Document(_Model):
    id: uuid.UUID
    dossier_id: uuid.UUID
    name: str
    size: int
    mimetype: str
    label: str | None = None
    text_extraction_status: str | None = None
    pages: list[Page_] = []


class Dossier(_Model):
    id: uuid.UUID
    name: str
    analyse_id: uuid.UUID | None = None
    created_at: datetime
    status: DossierStatus
    started_at: datetime | None = None
    ended_at: datetime | None = None
    execution_steps: list[ExecutionStep] = []
    documents: list[Document] = []


class AppToken(_Model):
    id: uuid.UUID
    name: str
    created_by: str
    created_at: datetime
    revoked_at: datetime | None = None
    last_used_at: datetime | None = None


class CreatedAppToken(AppToken):
    """Renvoyé à la création uniquement : `token` (en clair) n'est jamais réaffiché."""

    token: str


class LlmModel(_Model):
    id: str
