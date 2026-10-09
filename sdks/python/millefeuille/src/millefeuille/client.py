from __future__ import annotations

from types import TracebackType

import httpx

from millefeuille._http import DEFAULT_TIMEOUT, HTTPClient
from millefeuille.analyses import AnalysesResource
from millefeuille.dossiers import DossiersResource
from millefeuille.llm_models import ModelsResource
from millefeuille.tokens import AppTokensResource


class MilleFeuilleClient:
    """Client de l'API REST persistante de mille-feuille.

    Authentification (au moins une méthode) :

    - `api_token` : jeton applicatif, envoyé dans `X-App-Token` (comptes de service).
    - `bearer_token` : access token Keycloak (`Authorization: Bearer`).
    - `session_cookie` : valeur du cookie de session Keycloak `millefeuille_session`.

    Note : à ce jour, le backend n'accepte `X-App-Token` que sur `/api/ephemeral/*` et `/api/internal/*` ;
    les routes de ce client (`/api/analyses`, `/api/dossiers`, …) exigent `bearer_token` ou `session_cookie`.

    Les erreurs 5xx et réseau sont retentées avec backoff exponentiel sur les méthodes idempotentes
    (GET/PUT/DELETE) ; les POST ne sont jamais rejoués pour éviter les doublons.
    """

    def __init__(
        self,
        base_url: str,
        *,
        api_token: str | None = None,
        bearer_token: str | None = None,
        session_cookie: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not (api_token or bearer_token or session_cookie):
            raise ValueError("Fournir api_token, bearer_token ou session_cookie.")
        self._http = HTTPClient(
            base_url=base_url,
            api_token=api_token,
            bearer_token=bearer_token,
            session_cookie=session_cookie,
            timeout=timeout,
            max_retries=max_retries,
            backoff_factor=backoff_factor,
            transport=transport,
        )
        self.analyses = AnalysesResource(self._http)
        self.dossiers = DossiersResource(self._http)
        self.tokens = AppTokensResource(self._http)
        self.models = ModelsResource(self._http)

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> MilleFeuilleClient:
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None
    ) -> None:
        self.close()
