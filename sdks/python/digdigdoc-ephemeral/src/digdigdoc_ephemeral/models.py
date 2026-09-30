"""Modèles de l'API éphémère (alignés sur backend/app/schemas/ephemeral.py)."""

from __future__ import annotations

from datetime import datetime

from digdigdoc.models import Analyse, Dossier, EntityDefinition, LabelDefinition
from pydantic import BaseModel, ConfigDict, Field

TTL_DEFAULT_HOURS = 24
TTL_MAX_HOURS = 17520  # 2 ans


class AgentDefinition(BaseModel):
    """Agent créé en même temps que l'analyse (`prompt` obligatoire)."""

    name: str
    prompt: str = Field(min_length=1)
    # lecture_document | recherche_web | base_connaissances | appel_agent | calculatrice | verification_coherence
    tools: list[str] = []
    output: bool = True
    model: str | None = None


class EphemeralAnalysisConfig(BaseModel):
    """Définition complète d'une analyse éphémère, créée en un seul appel.

    Les listes acceptent des dicts (`{"name": "CNI", "definition": "..."}`) ou les modèles typés.
    """

    name: str
    description: str = ""
    persist: bool = False
    classification_prompt: str = ""
    labels: list[LabelDefinition] = []
    extraction_prompt: str = ""
    entities: list[EntityDefinition] = []
    agents: list[AgentDefinition] = []


class EphemeralAnalyse(Analyse):
    """Analyse + métadonnées de TTL. `expires_at` est `None` si `persist` ou tant qu'aucun run n'a fini."""

    model_config = ConfigDict(extra="allow")

    persist: bool
    expires_at: datetime | None = None


class EphemeralRun(Dossier):
    """Run (dossier) éphémère. `expires_at` = fin du run + `ttl_hours`, `None` tant qu'il n'est pas terminé."""

    model_config = ConfigDict(extra="allow")

    persist: bool
    ttl_hours: int | None = None
    expires_at: datetime | None = None
