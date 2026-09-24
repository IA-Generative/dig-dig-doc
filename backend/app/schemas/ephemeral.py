import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.analyse import AgentCreate, AnalyseOut, EntityDefinitionIn, LabelDefinitionIn
from app.schemas.dossier import DossierOut


class EphemeralAnalyseCreate(BaseModel):
    name: str = Field(examples=["Analyse CNI + justificatif"])
    description: str = ""
    # False par défaut : purgée au TTL comme le reste de la ressource
    # éphémère. True = conservée indéfiniment, comme une Analyse classique.
    persist: bool = Field(
        default=False,
        description="False (défaut) : purgée automatiquement une fois son TTL écoulé, comme tout le reste de "
        "l'API éphémère. True : conservée indéfiniment, comme une Analyse classique de la plateforme.",
    )
    classification_prompt: str = ""
    labels: list[LabelDefinitionIn] = []
    extraction_prompt: str = ""
    entities: list[EntityDefinitionIn] = []
    agents: list[AgentCreate] = Field(
        default=[],
        description="Chaque agent est créé en une seule fois avec l'analyse - pas d'étape séparée "
        "contrairement au flux de création standard de la plateforme (POST /api/analyses puis PUT/POST par champ).",
    )

    @field_validator("name")
    @classmethod
    def _name_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Le nom ne peut pas être vide.")
        return value


class EphemeralAnalyseCreated(BaseModel):
    analyse_id: uuid.UUID = Field(description="À réutiliser tel quel dans le flux A (.../analyses/{id}/runs).")


class EphemeralAnalyseOut(AnalyseOut):
    """AnalyseOut + les métadonnées propres à l'analyse éphémère
    (analyse_ephemere) - expires_at suit le TTL du dernier run l'ayant
    utilisée (voir docs/ephemeral-api.md, section "Principe du TTL")."""

    persist: bool
    expires_at: datetime | None = Field(
        description="NULL tant qu'aucun run n'a référencé cette analyse et n'est arrivé à son terme, ou si "
        "persist=True. Sinon : date/heure de fin du dernier run terminé qui l'a utilisée, plus son ttl_hours."
    )


class EphemeralRunCreated(BaseModel):
    run_id: uuid.UUID = Field(description="À utiliser avec GET/POST .../stop/DELETE /api/ephemeral/runs/{id}.")


class EphemeralRunOut(DossierOut):
    """DossierOut + les métadonnées propres au run éphémère (dossier_ephemere)
    - expires_at reste `None` tant que le run n'a pas atteint un état
    terminal (voir docs/ephemeral-api.md, section "Principe du TTL")."""

    persist: bool
    ttl_hours: int | None = Field(description="Valeur effective utilisée pour ce run (défaut 24h, max 17520h).")
    expires_at: datetime | None = Field(
        description="NULL tant que le run est en_attente/en_cours (le TTL démarre à la fin de l'analyse, pas à "
        "la création), ou si persist=True. Sinon : ended_at + ttl_hours, figé une fois calculé."
    )
