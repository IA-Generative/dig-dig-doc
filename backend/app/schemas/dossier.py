import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.conversation import MessageRole
from app.models.document_page import PredictionKind, PredictionValidationStatus
from app.models.dossier import DossierStatus, ExecutionStepKind, ExecutionStepStatus
from app.models.execution_log import ExecutionLogLevel


class BoundingBoxIn(BaseModel):
    x_min: float
    y_min: float
    x_max: float
    y_max: float


class BoundingBoxOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    x_min: float
    y_min: float
    x_max: float
    y_max: float


class DocumentPageSummaryOut(BaseModel):
    """Référence légère à une page, utilisée dans les schémas qui pointent
    vers un ensemble de pages (prédiction, source de message) - la page
    complète (avec ses prédictions) est déjà accessible via DossierOut."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    page_number: int


class PredictionValidationIn(BaseModel):
    status: PredictionValidationStatus
    corrected_value: str | None = None
    bounding_box: BoundingBoxIn | None = None


class PredictionValidationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    validator_user_id: str
    status: PredictionValidationStatus
    corrected_value: str | None
    bounding_box: BoundingBoxOut | None
    created_at: datetime


class DocumentPredictionSummaryOut(BaseModel):
    """Vue nichée dans DocumentPageOut.predictions : pas de `pages` ici (on
    est déjà sous une page) - la liste complète des pages d'une entité qui
    s'étend sur plusieurs d'entre elles n'est disponible que sur la
    prédiction elle-même (DocumentPredictionOut, endpoints dédiés)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: PredictionKind
    name: str
    value: str
    confidence: float | None
    # Présent seulement si la définition existe encore (voir le commentaire
    # sur DocumentPrediction.label_definition_id/entity_definition_id).
    label_definition_id: uuid.UUID | None
    entity_definition_id: uuid.UUID | None
    # Une classification n'a qu'un élément ; une entité peut n'être
    # localisée que par plusieurs zones, potentiellement sur d'autres pages.
    bounding_boxes: list[BoundingBoxOut]
    validations: list[PredictionValidationOut]


class DocumentPredictionOut(DocumentPredictionSummaryOut):
    # Une classification n'a qu'un élément ; une entité peut s'étendre sur
    # plusieurs pages.
    pages: list[DocumentPageSummaryOut]


class DocumentPageIn(BaseModel):
    page_number: int
    width: int | None = None
    height: int | None = None
    content: str | None = None
    # Clé S3 de la capture de la page, déjà uploadée par le worker (voir
    # storage.put_object) au moment de cet appel - jamais renvoyée telle
    # quelle par l'API, uniquement via GET .../pages/{id}/screenshot.
    screenshot_key: str | None = None


class DocumentPredictionIn(BaseModel):
    kind: PredictionKind
    name: str
    value: str
    confidence: float | None = None
    label_definition_id: uuid.UUID | None = None
    entity_definition_id: uuid.UUID | None = None
    # Pages/bbox additionnelles au-delà de la page de l'URL (POST
    # .../pages/{page_id}/predictions) : toujours incluse dans le résultat,
    # inutile de la répéter ici. Les bbox doivent déjà exister (voir POST
    # .../pages/{page_id}/bounding-boxes).
    page_ids: list[uuid.UUID] = []
    bounding_box_ids: list[uuid.UUID] = []


class MessageSourceIn(BaseModel):
    dossier_document_id: uuid.UUID | None = None
    execution_step_id: uuid.UUID | None = None
    excerpt: str | None = None
    # Du plus large au plus précis : le document ci-dessus suffit à minima,
    # mais la réponse peut citer un ensemble de pages ou, plus précisément,
    # un ensemble de bbox (déjà créées) sur ces pages.
    page_ids: list[uuid.UUID] = []
    bounding_box_ids: list[uuid.UUID] = []


class InternalMessageIn(BaseModel):
    content: str
    sources: list[MessageSourceIn] = []


class DocumentPageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    page_number: int
    width: int | None
    height: int | None
    content: str | None
    has_screenshot: bool
    bounding_boxes: list[BoundingBoxOut]
    predictions: list[DocumentPredictionSummaryOut]


class DossierDocumentIn(BaseModel):
    name: str
    size: int
    s3_key: str
    mimetype: str


class DossierDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    size: int
    s3_key: str
    mimetype: str
    label: str | None
    pages: list[DocumentPageOut]


class DossierDocumentLabelIn(BaseModel):
    label: str | None


class MessageSourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dossier_document_id: uuid.UUID | None
    execution_step_id: uuid.UUID | None
    excerpt: str | None
    pages: list[DocumentPageSummaryOut]
    bounding_boxes: list[BoundingBoxOut]


class MessageIn(BaseModel):
    content: str


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: MessageRole
    content: str
    created_at: datetime
    sources: list[MessageSourceOut]


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dossier_id: uuid.UUID
    user_id: str
    created_at: datetime
    messages: list[MessageOut]


class ExecutionLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    level: ExecutionLogLevel
    message: str
    created_at: datetime


class ExecutionStepOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: ExecutionStepKind
    label: str
    status: ExecutionStepStatus
    started_at: datetime
    ended_at: datetime | None
    output: str | None
    logs: list[ExecutionLogOut]


class ExecutionStepCompleteIn(BaseModel):
    status: ExecutionStepStatus
    output: str | None = None


class ExecutionLogIn(BaseModel):
    level: ExecutionLogLevel = ExecutionLogLevel.INFO
    message: str


class DossierCreate(BaseModel):
    name: str
    analyse_id: uuid.UUID


class DossierOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    analyse_id: uuid.UUID
    analyse_version: str
    created_at: datetime
    status: DossierStatus
    started_at: datetime | None
    ended_at: datetime | None
    execution_steps: list[ExecutionStepOut]
    documents: list[DossierDocumentOut]
