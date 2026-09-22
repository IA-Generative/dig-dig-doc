import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.conversation import MessageRole
from app.models.dossier import DossierStatus, ExecutionStepKind, ExecutionStepStatus


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


class DossierDocumentLabelIn(BaseModel):
    label: str | None


class MessageIn(BaseModel):
    content: str


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: MessageRole
    content: str
    created_at: datetime


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dossier_id: uuid.UUID
    user_id: str
    created_at: datetime
    messages: list[MessageOut]


class ExecutionStepOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: ExecutionStepKind
    label: str
    status: ExecutionStepStatus
    started_at: datetime
    ended_at: datetime | None
    output: str | None


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
