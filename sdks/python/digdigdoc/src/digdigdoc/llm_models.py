from __future__ import annotations

from typing import TYPE_CHECKING

from digdigdoc.models import LlmModel

if TYPE_CHECKING:
    from digdigdoc._http import HTTPClient


class ModelsResource:
    """Ressource `/api/models` (modèles LLM disponibles pour les agents)."""

    def __init__(self, http: HTTPClient) -> None:
        self._http = http

    def list(self) -> list[LlmModel]:
        data = self._http.get_json("/models")
        return [LlmModel.model_validate(item) for item in data["models"]]
