import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.analyse import AgentTool, EntityType


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
