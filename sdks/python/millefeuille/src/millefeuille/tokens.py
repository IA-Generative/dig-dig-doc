from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from millefeuille.models import AppToken, AppTokenCreate, CreatedAppToken, Page

if TYPE_CHECKING:
    from millefeuille._http import HTTPClient


class AppTokensResource:
    """Ressource `/api/app-tokens`. Réservée à une session/jeton Keycloak (pas à un token API)."""

    def __init__(self, http: HTTPClient) -> None:
        self._http = http

    def list(self, page: int = 1, page_size: int = 20) -> Page[AppToken]:
        data = self._http.get_json("/app-tokens", params={"page": page, "page_size": page_size})
        return Page[AppToken].model_validate(data)

    def create(self, name: str) -> CreatedAppToken:
        """Crée un token. `token` (en clair) n'est renvoyé qu'ici, une seule fois."""
        body = AppTokenCreate(name=name)
        return CreatedAppToken.model_validate(
            self._http.request("POST", "/app-tokens", json=body.model_dump(mode="json")).json()
        )

    def revoke(self, token_id: uuid.UUID | str) -> None:
        self._http.request("DELETE", f"/app-tokens/{token_id}")
