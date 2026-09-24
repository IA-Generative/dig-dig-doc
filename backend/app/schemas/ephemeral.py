import uuid

from pydantic import BaseModel, field_validator

from app.schemas.analyse import AgentCreate, EntityDefinitionIn, LabelDefinitionIn


class EphemeralAnalyseCreate(BaseModel):
    name: str
    description: str = ""
    # False par défaut : purgée au TTL comme le reste de la ressource
    # éphémère. True = conservée indéfiniment, comme une Analyse classique.
    persist: bool = False
    classification_prompt: str = ""
    labels: list[LabelDefinitionIn] = []
    extraction_prompt: str = ""
    entities: list[EntityDefinitionIn] = []
    agents: list[AgentCreate] = []

    @field_validator("name")
    @classmethod
    def _name_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Le nom ne peut pas être vide.")
        return value


class EphemeralAnalyseCreated(BaseModel):
    analyse_id: uuid.UUID
