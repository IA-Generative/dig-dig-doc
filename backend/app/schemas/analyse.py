import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.analyse import AgentTool, EntityType
from app.models.analyse_share import AnalyseShareKind


class Version[T](BaseModel):
    id: uuid.UUID
    content: T
    created_at: datetime


class LabelDefinitionIn(BaseModel):
    name: str
    definition: str = ""


class LabelDefinitionOut(LabelDefinitionIn):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID


class EntityDefinitionIn(BaseModel):
    name: str
    definition: str = ""
    type: EntityType


class EntityDefinitionOut(EntityDefinitionIn):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID


class ClassificationOut(BaseModel):
    prompt: str
    prompt_versions: list[Version[str]]
    labels: list[LabelDefinitionOut]
    labels_versions: list[Version[list[LabelDefinitionOut]]]


class ExtractionOut(BaseModel):
    prompt: str
    prompt_versions: list[Version[str]]
    entities: list[EntityDefinitionOut]
    entities_versions: list[Version[list[EntityDefinitionOut]]]


class AgentCreate(BaseModel):
    name: str
    prompt: str
    tools: list[AgentTool] = []
    output: bool = True
    # Identifiant de modèle tel que renvoyé par GET /models ; None = pas de
    # préférence, le hub par défaut sera utilisé.
    model: str | None = None


class AgentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class AnalyseCreate(BaseModel):
    name: str
    description: str = ""


class AnalyseListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str
    created_at: datetime
    agent_count: int


class AnalyseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str
    created_at: datetime
    classification: ClassificationOut
    extraction: ExtractionOut
    agents: list[AgentOut]


class PromptUpdate(BaseModel):
    prompt: str


class LabelsUpdate(BaseModel):
    labels: list[LabelDefinitionIn]


class EntitiesUpdate(BaseModel):
    entities: list[EntityDefinitionIn]


class ToolsUpdate(BaseModel):
    tools: list[AgentTool]


class OutputUpdate(BaseModel):
    output: bool


class ModelUpdate(BaseModel):
    model: str | None


class AnalyseShareCreate(BaseModel):
    kind: AnalyseShareKind
    # kind == email :
    email: str | None = None
    expires_in_hours: int | None = None
    # kind == keycloak_group :
    keycloak_group: str | None = None


class AnalyseShareOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: AnalyseShareKind
    email: str | None
    keycloak_group: str | None
    expires_at: datetime | None
    created_by: str
    created_at: datetime
    # Uniquement renvoyé à la création d'un partage par email : le jeton en
    # clair n'est jamais stocké, donc jamais renvoyé ensuite.
    share_url: str | None = None
