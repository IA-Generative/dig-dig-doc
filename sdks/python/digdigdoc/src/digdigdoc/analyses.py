from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from digdigdoc.models import Analyse, AnalyseListItem, Page

if TYPE_CHECKING:
    from digdigdoc._http import HTTPClient


class AnalysesResource:
    """Ressource `/api/analyses` (analyses persistantes)."""

    def __init__(self, http: HTTPClient) -> None:
        self._http = http

    def list(self, page: int = 1, page_size: int = 20, q: str | None = None) -> Page[AnalyseListItem]:
        """Liste paginée ; `q` filtre par nom (insensible à la casse)."""
        data = self._http.get_json("/analyses", params={"page": page, "page_size": page_size, "q": q})
        return Page[AnalyseListItem].model_validate(data)

    def get(self, analyse_id: uuid.UUID | str) -> Analyse:
        """Définition complète : classification, extraction, agents."""
        return Analyse.model_validate(self._http.get_json(f"/analyses/{analyse_id}"))

    def create(self, name: str, description: str) -> Analyse:
        """Crée une analyse (nom + description, tous deux obligatoires côté serveur)."""
        response = self._http.request("POST", "/analyses", json={"name": name, "description": description})
        return Analyse.model_validate(response.json())

    def delete(self, analyse_id: uuid.UUID | str) -> None:
        self._http.request("DELETE", f"/analyses/{analyse_id}")
