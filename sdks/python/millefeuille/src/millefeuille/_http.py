"""Client HTTP de base : authentification, gestion d'erreurs, retry."""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from typing import Any

import httpx

from millefeuille.exceptions import (
    AuthenticationError,
    ConflictError,
    ConnectionFailedError,
    MilleFeuilleError,
    NotFoundError,
    ServerError,
    ValidationError,
)

SESSION_COOKIE_NAME = "millefeuille_session"
DEFAULT_TIMEOUT = 30.0
# Rejouer un POST pourrait créer deux fois la même ressource : seules les
# méthodes idempotentes sont retentées sur 5xx / erreur réseau.
_IDEMPOTENT_METHODS = frozenset({"GET", "HEAD", "PUT", "DELETE", "OPTIONS"})

FileTuple = tuple[str, tuple[str, bytes, str]]


def normalize_base_url(base_url: str) -> str:
    """Accepte `https://host` ou `https://host/api` et renvoie toujours `https://host/api`."""
    url = base_url.rstrip("/")
    return url if url.endswith("/api") else f"{url}/api"


def _error_message(response: httpx.Response) -> str:
    try:
        detail = response.json().get("detail")
    except (ValueError, AttributeError):
        detail = None
    if isinstance(detail, str):
        return detail
    if detail is not None:
        return str(detail)
    return response.text or response.reason_phrase


def raise_for_status(response: httpx.Response) -> None:
    """Convertit une réponse HTTP en erreur en exception typée."""
    status = response.status_code
    if status < 400:
        return
    message = _error_message(response)
    kwargs: dict[str, Any] = {"status_code": status, "response": response}
    if status in (401, 403):
        raise AuthenticationError(message, **kwargs)
    if status == 404:
        raise NotFoundError(message, **kwargs)
    if status == 409:
        raise ConflictError(message, **kwargs)
    if status in (400, 422):
        raise ValidationError(message, **kwargs)
    if status >= 500:
        raise ServerError(message, **kwargs)
    raise MilleFeuilleError(message, **kwargs)


class HTTPClient:
    """Enveloppe `httpx.Client` : URL de base, en-têtes d'auth, erreurs typées, retry."""

    def __init__(
        self,
        *,
        base_url: str,
        api_token: str | None = None,
        bearer_token: str | None = None,
        session_cookie: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        headers: dict[str, str] = {}
        cookies: dict[str, str] = {}
        if api_token:
            headers["X-App-Token"] = api_token
        if bearer_token:
            headers["Authorization"] = f"Bearer {bearer_token}"
        if session_cookie:
            cookies[SESSION_COOKIE_NAME] = session_cookie
        self._client = httpx.Client(
            base_url=normalize_base_url(base_url),
            headers=headers,
            cookies=cookies,
            timeout=timeout,
            transport=transport,
        )
        self._max_retries = max_retries
        self._backoff_factor = backoff_factor
        self._sleep = sleep

    def close(self) -> None:
        self._client.close()

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Any = None,
        data: Mapping[str, Any] | None = None,
        files: list[FileTuple] | None = None,
    ) -> httpx.Response:
        method = method.upper()
        retries = self._max_retries if method in _IDEMPOTENT_METHODS else 0
        clean_params = {k: v for k, v in (params or {}).items() if v is not None}
        # httpx sérialise les booléens en "True"/"False" : FastAPI attend "true"/"false".
        clean_data = {k: str(v).lower() if isinstance(v, bool) else v for k, v in (data or {}).items()}
        attempt = 0
        while True:
            try:
                response = self._client.request(
                    method, path, params=clean_params, json=json, data=clean_data or None, files=files
                )
            except httpx.TransportError as error:
                if attempt >= retries:
                    raise ConnectionFailedError(f"{method} {path} : {error}") from error
            else:
                if response.status_code < 500 or attempt >= retries:
                    raise_for_status(response)
                    return response
            self._sleep(self._backoff_factor * 2**attempt)
            attempt += 1

    def get_json(self, path: str, **kwargs: Any) -> Any:
        return self.request("GET", path, **kwargs).json()
