from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx
import pytest
from contract import example

from digdigdoc import DigDigDocClient

NOW = "2026-09-30T10:00:00Z"


def analyse_json(analyse_id: str | None = None, name: str = "A") -> dict[str, Any]:
    """Réponse `AnalyseOut` générée depuis l'OpenAPI du backend."""
    return example("AnalyseOut", **({"id": analyse_id} if analyse_id else {}), name=name)


def dossier_json(dossier_id: str | None = None, status: str = "en_attente") -> dict[str, Any]:
    """Réponse `DossierOut` générée depuis l'OpenAPI du backend."""
    return example("DossierOut", **({"id": dossier_id} if dossier_id else {}), status=status)


@pytest.fixture
def make_client() -> Callable[..., tuple[DigDigDocClient, list[httpx.Request]]]:
    def factory(
        handler: Callable[[httpx.Request], httpx.Response], **kwargs: Any
    ) -> tuple[DigDigDocClient, list[httpx.Request]]:
        seen: list[httpx.Request] = []

        def recording(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return handler(request)

        kwargs.setdefault("bearer_token", "tok")
        kwargs.setdefault("backoff_factor", 0)
        client = DigDigDocClient("https://api.test", transport=httpx.MockTransport(recording), **kwargs)
        return client, seen

    return factory
