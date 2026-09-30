"""Modèles d'entrée et de sortie, alignés champ par champ sur backend/app/schemas/.

- Sorties (`*Out`, `Dossier`, `Analyse`…) : tous les champs du backend sont typés, les valeurs
  fermées sont des enums. Un champ inconnu est ignoré ; une valeur hors enum lève une erreur pydantic.
- Entrées (`*Create`, `*In`) : mêmes validations que le backend (champs obligatoires, textes non
  vides) et champs inconnus refusés, pour détecter les fautes de frappe avant l'appel réseau.

`tests/test_contract.py` compare ces modèles à l'OpenAPI du backend (`tests/openapi.json`).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _Out(BaseModel):
    """Base des modèles de réponse."""

    model_config = ConfigDict(extra="ignore")


class _In(BaseModel):
    """Base des modèles de requête."""

    model_config = ConfigDict(extra="forbid")


# --- Enums -------------------------------------------------------------------------------------


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


class ExecutionStepKind(StrEnum):
    CLASSIFICATION = "classification"
    EXTRACTION = "extraction"
    AGENT = "agent"


class ExecutionStepStatus(StrEnum):
    EN_COURS = "en_cours"
    TERMINE = "terminé"
    ECHEC = "échec"


class ExecutionLogLevel(StrEnum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class TextExtractionStatus(StrEnum):
    EN_ATTENTE = "en_attente"
    EN_COURS = "en_cours"
    TERMINE = "terminé"
    ECHEC = "échec"


class SummaryStatus(StrEnum):
    EN_ATTENTE = "en_attente"
    EN_COURS = "en_cours"
    TERMINE = "terminé"
    ECHEC = "échec"


class SuggestionStatus(StrEnum):
    EN_ATTENTE = "en_attente"
    EN_COURS = "en_cours"
    TERMINE = "terminé"
    ECHEC = "échec"


class PredictionKind(StrEnum):
    LABEL = "label"
    ENTITY = "entity"


class PredictionValidationStatus(StrEnum):
    VALIDE = "validé"
    CORRIGE = "corrigé"
    REJETE = "rejeté"


class EntityType(StrEnum):
    TEXTE = "texte"
    DATE = "date"
    NOMBRE = "nombre"
    BOOLEEN = "booléen"
    IDENTIFIANT = "identifiant"


class AgentTool(StrEnum):
    LECTURE_DOCUMENT = "lecture_document"
    RECHERCHE_WEB = "recherche_web"
    BASE_CONNAISSANCES = "base_connaissances"
    APPEL_AGENT = "appel_agent"
    CALCULATRICE = "calculatrice"
    VERIFICATION_COHERENCE = "verification_coherence"


# --- Entrées -----------------------------------------------------------------------------------


class LabelDefinitionIn(_In):
    name: str
    definition: str = ""


class EntityDefinitionIn(_In):
    name: str
    definition: str = ""
    type: EntityType


class AgentCreate(_In):
    """Agent : `prompt` obligatoire et non vide (il sert de consigne au modèle)."""

    name: str
    prompt: str = Field(min_length=1)
    tools: list[AgentTool] = []
    output: bool = True
    # Identifiant renvoyé par `client.models.list()` ; None = modèle par défaut du hub.
    model: str | None = None

    @field_validator("prompt")
    @classmethod
    def _prompt_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("La description (prompt) ne peut pas être vide.")
        return value


class AnalyseCreate(_In):
    name: str
    description: str = Field(min_length=1)

    @field_validator("description")
    @classmethod
    def _description_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("La description ne peut pas être vide.")
        return value


class DossierCreate(_In):
    name: str
    analyse_id: uuid.UUID | None = None


class AppTokenCreate(_In):
    name: str


# --- Sorties -----------------------------------------------------------------------------------


class Page[T](_Out):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


class Version[T](_Out):
    id: uuid.UUID
    content: T
    created_at: datetime


class LabelDefinition(_Out):
    id: uuid.UUID
    name: str
    definition: str = ""


class EntityDefinition(_Out):
    id: uuid.UUID
    name: str
    definition: str = ""
    type: EntityType


class Classification(_Out):
    prompt: str
    prompt_versions: list[Version[str]]
    labels: list[LabelDefinition]
    labels_versions: list[Version[list[LabelDefinition]]]


class Extraction(_Out):
    prompt: str
    prompt_versions: list[Version[str]]
    entities: list[EntityDefinition]
    entities_versions: list[Version[list[EntityDefinition]]]


class Agent(_Out):
    id: uuid.UUID
    name: str
    prompt: str
    prompt_versions: list[Version[str]]
    tools: list[AgentTool]
    tools_versions: list[Version[list[AgentTool]]]
    output: bool
    output_versions: list[Version[bool]]
    model: str | None
    model_versions: list[Version[str | None]]


class AnalyseListItem(_Out):
    id: uuid.UUID
    name: str
    description: str
    created_at: datetime
    agent_count: int


class Analyse(_Out):
    id: uuid.UUID
    name: str
    description: str
    created_at: datetime
    classification: Classification
    extraction: Extraction
    agents: list[Agent]


class ExecutionLog(_Out):
    id: uuid.UUID
    level: ExecutionLogLevel
    message: str
    created_at: datetime


class ExecutionStep(_Out):
    id: uuid.UUID
    kind: ExecutionStepKind
    label: str
    status: ExecutionStepStatus
    started_at: datetime
    ended_at: datetime | None
    output: str | None
    logs: list[ExecutionLog]


class BoundingBox(_Out):
    id: uuid.UUID
    x_min: float
    y_min: float
    x_max: float
    y_max: float


class PredictionValidation(_Out):
    id: uuid.UUID
    validator_user_id: str
    status: PredictionValidationStatus
    corrected_value: str | None
    bounding_box: BoundingBox | None
    created_at: datetime


class Prediction(_Out):
    id: uuid.UUID
    kind: PredictionKind
    name: str
    value: str
    confidence: float | None
    label_definition_id: uuid.UUID | None
    entity_definition_id: uuid.UUID | None
    bounding_boxes: list[BoundingBox]
    validations: list[PredictionValidation]


class DocumentPage(_Out):
    id: uuid.UUID
    page_number: int
    width: int | None
    height: int | None
    content: str | None
    has_screenshot: bool
    bounding_boxes: list[BoundingBox]
    predictions: list[Prediction]


class Summary(_Out):
    """Résumé (de document ou de dossier) ; le plus récent fait foi."""

    id: uuid.UUID
    content: str
    model: str | None
    created_at: datetime


class Document(_Out):
    id: uuid.UUID
    dossier_id: uuid.UUID
    name: str
    size: int
    s3_key: str
    mimetype: str
    label: str | None
    text_extraction_status: TextExtractionStatus
    text_extraction_error: str | None
    file_hash: str | None
    summary_status: SummaryStatus
    summary_error: str | None
    summary: Summary | None = None
    pages: list[DocumentPage]


class Dossier(_Out):
    id: uuid.UUID
    name: str
    analyse_id: uuid.UUID | None
    analyse_version: str
    created_at: datetime
    status: DossierStatus
    started_at: datetime | None
    ended_at: datetime | None
    summary_status: SummaryStatus
    summary_error: str | None
    summary: Summary | None = None
    suggested_analyses: list[dict[str, Any]] | None = None
    suggestion_status: SuggestionStatus
    execution_steps: list[ExecutionStep]
    documents: list[Document]


class AppToken(_Out):
    id: uuid.UUID
    name: str
    created_by: str
    created_at: datetime
    revoked_at: datetime | None
    last_used_at: datetime | None


class CreatedAppToken(AppToken):
    """Renvoyé à la création uniquement : `token` (en clair) n'est jamais réaffiché."""

    token: str


class LlmModel(_Out):
    id: str


class LlmModelsResponse(_Out):
    models: list[LlmModel]
