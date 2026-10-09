from __future__ import annotations

from typing import TYPE_CHECKING

from millefeuille.models import LlmModel, LlmModelsResponse

if TYPE_CHECKING:
    from millefeuille._http import HTTPClient


class ModelsResource:
    """Ressource `/api/models` (modèles LLM disponibles pour les agents)."""

    def __init__(self, http: HTTPClient) -> None:
        self._http = http

    def list(self) -> list[LlmModel]:
        return LlmModelsResponse.model_validate(self._http.get_json("/models")).models
