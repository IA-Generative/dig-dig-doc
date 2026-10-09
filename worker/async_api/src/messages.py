"""Contrat d'entrée de la tâche (à garder aligné avec `contrat.json`)."""

import uuid
from typing import Self

from millefeuille_ephemeral import EphemeralAnalysisConfig
from millefeuille_ephemeral.models import TTL_DEFAULT_HOURS, TTL_MAX_HOURS
from pydantic import BaseModel, ConfigDict, Field, model_validator


class FileRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Clé S3 du fichier, déposé au préalable dans le stockage d'AsyncTaskAPI.
    file_id: str = Field(min_length=1, max_length=1024)
    # Nom d'affichage côté mille-feuille ; par défaut, le dernier segment de `file_id`.
    name: str | None = Field(default=None, min_length=1)

    @property
    def display_name(self) -> str:
        return self.name or self.file_id.rsplit("/", 1)[-1]


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Définition complète créée à la volée, OU identifiant d'une analyse existante : exactement un des deux.
    analysis: EphemeralAnalysisConfig | None = None
    analyse_id: uuid.UUID | None = None
    files: list[FileRef] = Field(min_length=1)
    ttl_hours: int = Field(default=TTL_DEFAULT_HOURS, ge=1, le=TTL_MAX_HOURS)
    persist: bool = False

    @model_validator(mode="after")
    def _exactly_one_analysis_source(self) -> Self:
        if (self.analysis is None) == (self.analyse_id is None):
            raise ValueError("Fournir exactement un de `analysis` ou `analyse_id`.")
        return self
