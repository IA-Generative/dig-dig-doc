from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserPreferenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    theme: str = Field(description="Thème DSFR: light, dark ou system")


class UserPreferenceUpdate(BaseModel):
    theme: str = Field(description="Thème DSFR: light, dark ou system")


class UserStats(BaseModel):
    """Statistiques personnelles de l'utilisateur courant."""

    conversations_count: int = Field(description="Nombre de conversations avec l'assistant (dossiers)")
    messages_sent_count: int = Field(description="Nombre total de messages envoyés (utilisateur)")
    agent_conversations_count: int = Field(description="Nombre de conversations avec l'agent helper")
    agent_messages_sent_count: int = Field(description="Nombre total de messages envoyés à l'agent helper")
    dossiers_count: int = Field(description="Nombre de dossiers distincts accessibles")
    analyses_shared_count: int = Field(description="Nombre d'analyses partagées par l'utilisateur")
    last_activity_at: datetime | None = Field(description="Date de dernière activité (dernier message)")
