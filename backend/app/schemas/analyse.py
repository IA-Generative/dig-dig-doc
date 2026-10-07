import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

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


# Couleur d'un statut : #RRGGBB.
HEX_COLOR_PATTERN = r"^#[0-9a-fA-F]{6}$"


class StatusDefinitionIn(BaseModel):
    # Absent pour un nouveau statut ; fourni pour conserver l'identité d'un statut existant
    # (les dossiers y font référence).
    id: uuid.UUID | None = None
    name: str
    color: str = Field(default="#6a6af4", pattern=HEX_COLOR_PATTERN)
    is_initial: bool = False
    is_final: bool = False

    @field_validator("name")
    @classmethod
    def _name_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Le nom d'un statut ne peut pas être vide.")
        return value


class StatusDefinitionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    color: str
    position: int
    is_initial: bool
    is_final: bool


class DueStepIn(BaseModel):
    """Un seuil d'échéance : « N jours restants ou moins » prend cette couleur."""

    days: int = Field(ge=1, le=3650)
    color: str = Field(pattern=HEX_COLOR_PATTERN)


class DueThresholdsIn(BaseModel):
    """Couleurs de l'échéance : loin, chaque seuil (du plus large au plus serré), dépassée."""

    far_color: str = Field(default="#18753c", pattern=HEX_COLOR_PATTERN)
    steps: list[DueStepIn] = Field(default_factory=list, max_length=5)
    overdue_color: str = Field(default="#8a0000", pattern=HEX_COLOR_PATTERN)

    @field_validator("steps")
    @classmethod
    def _steps_must_be_distinct(cls, steps: list[DueStepIn]) -> list[DueStepIn]:
        days = [step.days for step in steps]
        if len(set(days)) != len(days):
            raise ValueError("Deux seuils ne peuvent pas avoir le même nombre de jours.")
        return sorted(steps, key=lambda step: step.days, reverse=True)


class DueSettingsIn(BaseModel):
    # Durée par défaut, en jours depuis la création du dossier ; absente = pas d'échéance automatique.
    default_due_days: int | None = Field(default=None, ge=1, le=3650)
    thresholds: DueThresholdsIn


class DueSettingsOut(DueSettingsIn):
    pass


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
    # La description est obligatoire : elle décrit précisément le but métier
    # de l'agent et sert de prompt au modèle de langage lors de l'exécution.
    prompt: str = Field(min_length=1)
    tools: list[AgentTool] = []
    output: bool = True
    # Identifiant de modèle tel que renvoyé par GET /models ; None = pas de
    # préférence, le hub par défaut sera utilisé.
    model: str | None = None

    @field_validator("prompt")
    @classmethod
    def _prompt_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("La description (prompt) ne peut pas être vide.")
        return value


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
    # La description est obligatoire : elle décrit le but métier de
    # l'analyse et sert de prompt/instruction globale aux agents lors de
    # l'exécution.
    description: str = Field(min_length=1)

    @field_validator("description")
    @classmethod
    def _description_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("La description ne peut pas être vide.")
        return value


class AnalyseListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str
    created_at: datetime
    agent_count: int
    # Statuts de dossier de l'analyse (issue #168) : la liste des dossiers s'en sert pour son filtre.
    statuses: list["StatusDefinitionOut"] = []


class AnalyseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str
    created_at: datetime
    classification: ClassificationOut
    extraction: ExtractionOut
    # Statuts de dossier de l'analyse (issue #168), dans l'ordre, et leurs versions précédentes.
    statuses: list[StatusDefinitionOut] = []
    statuses_versions: list[Version[list[StatusDefinitionOut]]] = []
    # Échéance des dossiers (issue #172) : durée par défaut et seuils de couleur, avec leur historique.
    due_settings: DueSettingsOut | None = None
    due_settings_versions: list[Version[DueSettingsOut]] = []
    agents: list[AgentOut]


class PromptUpdate(BaseModel):
    prompt: str = Field(min_length=1)

    @field_validator("prompt")
    @classmethod
    def _prompt_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("La description (prompt) ne peut pas être vide.")
        return value


class LabelsUpdate(BaseModel):
    labels: list[LabelDefinitionIn]


class EntitiesUpdate(BaseModel):
    entities: list[EntityDefinitionIn]


class StatusesUpdate(BaseModel):
    statuses: list[StatusDefinitionIn]
    # Pour chaque statut supprimé encore utilisé par des dossiers : le statut qui les reprend.
    replacements: dict[uuid.UUID, uuid.UUID] = {}


class StatusesRestore(BaseModel):
    replacements: dict[uuid.UUID, uuid.UUID] = {}


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
