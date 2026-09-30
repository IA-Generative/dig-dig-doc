from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

import httpx
import pytest

from digdigdoc import DigDigDocClient

NOW = "2026-09-30T10:00:00Z"


def analyse_json(analyse_id: str | None = None, name: str = "A") -> dict[str, Any]:
    return {
        "id": analyse_id or str(uuid.uuid4()),
        "name": name,
        "description": "d",
        "created_at": NOW,
        "classification": {"prompt": "", "prompt_versions": [], "labels": [], "labels_versions": []},
        "extraction": {"prompt": "", "prompt_versions": [], "entities": [], "entities_versions": []},
        "agents": [],
    }


def dossier_json(dossier_id: str | None = None, status: str = "en_attente") -> dict[str, Any]:
    return {
        "id": dossier_id or str(uuid.uuid4()),
        "name": "D",
        "analyse_id": None,
        "created_at": NOW,
        "status": status,
        "started_at": None,
        "ended_at": None,
        "execution_steps": [],
        "documents": [],
    }


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
