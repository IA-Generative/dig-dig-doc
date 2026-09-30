from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from digdigdoc_ephemeral.models import EphemeralAnalyse, EphemeralAnalysisConfig

if TYPE_CHECKING:
    from digdigdoc._http import HTTPClient


class EphemeralAnalysesResource:
    """Ressource `/api/ephemeral/analyses`."""

    def __init__(self, http: HTTPClient) -> None:
        self._http = http

    def create(
        self,
        name: str,
        description: str = "",
        persist: bool = False,
        classification_prompt: str = "",
        labels: list[dict[str, str]] | None = None,
        extraction_prompt: str = "",
        entities: list[dict[str, str]] | None = None,
        agents: list[dict[str, object]] | None = None,
    ) -> EphemeralAnalyse:
        """Crée une analyse complète (classification, entités, agents) en un seul appel.

        `persist=False` : purgée automatiquement une fois le TTL de son dernier run écoulé.
        """
        config = EphemeralAnalysisConfig.model_validate(
            {
                "name": name,
                "description": description,
                "persist": persist,
                "classification_prompt": classification_prompt,
                "labels": labels or [],
                "extraction_prompt": extraction_prompt,
                "entities": entities or [],
                "agents": agents or [],
            }
        )
        return self.create_from_config(config)

    def create_from_config(self, config: EphemeralAnalysisConfig) -> EphemeralAnalyse:
        response = self._http.request(
            "POST", "/ephemeral/analyses", json=config.model_dump(mode="json", exclude_none=True)
        )
        return self.get(response.json()["analyse_id"])

    def get(self, analyse_id: uuid.UUID | str) -> EphemeralAnalyse:
        """Définition complète + `persist` + `expires_at`."""
        return EphemeralAnalyse.model_validate(self._http.get_json(f"/ephemeral/analyses/{analyse_id}"))

    def delete(self, analyse_id: uuid.UUID | str) -> None:
        """Suppression immédiate. `ConflictError` (409) si des runs y sont encore liés."""
        self._http.request("DELETE", f"/ephemeral/analyses/{analyse_id}")
