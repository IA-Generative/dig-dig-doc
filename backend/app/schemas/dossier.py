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


class DocumentPredictionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: PredictionKind
    name: str
    value: str
    confidence: float | None
    bounding_box: BoundingBoxOut | None
    validations: list[PredictionValidationOut]


class DocumentPageIn(BaseModel):
    page_number: int
    width: int | None = None
    height: int | None = None
    content: str | None = None


class DocumentPredictionIn(BaseModel):
    kind: PredictionKind
    name: str
    value: str
    confidence: float | None = None
    bounding_box: BoundingBoxIn | None = None


class MessageSourceIn(BaseModel):
    dossier_document_id: uuid.UUID | None = None
    execution_step_id: uuid.UUID | None = None
    excerpt: str | None = None


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
    bounding_boxes: list[BoundingBoxOut]
    predictions: list[DocumentPredictionOut]


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
