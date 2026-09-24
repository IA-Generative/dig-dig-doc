import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator

from app.schemas.analyse import AgentCreate, AnalyseOut, EntityDefinitionIn, LabelDefinitionIn
from app.schemas.dossier import DossierOut


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


class EphemeralAnalyseOut(AnalyseOut):
    """AnalyseOut + les métadonnées propres à l'analyse éphémère
    (analyse_ephemere) - expires_at suit le TTL du dernier run l'ayant
    utilisée (voir docs/ephemeral-api.md, section "Principe du TTL")."""

    persist: bool
    expires_at: datetime | None


class EphemeralRunCreated(BaseModel):
    run_id: uuid.UUID


class EphemeralRunOut(DossierOut):
    """DossierOut + les métadonnées propres au run éphémère (dossier_ephemere)
    - expires_at reste `None` tant que le run n'a pas atteint un état
    terminal (voir docs/ephemeral-api.md, section "Principe du TTL")."""

    persist: bool
    ttl_hours: int | None
    expires_at: datetime | None
