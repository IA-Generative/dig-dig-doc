from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

import httpx
import pytest

from digdigdoc_ephemeral import EphemeralClient

NOW = "2026-09-30T10:00:00Z"


def analyse_json(analyse_id: str | None = None, persist: bool = False) -> dict[str, Any]:
    return {
        "id": analyse_id or str(uuid.uuid4()),
        "name": "A",
        "description": "d",
        "created_at": NOW,
        "classification": {"prompt": "", "prompt_versions": [], "labels": [], "labels_versions": []},
        "extraction": {"prompt": "", "prompt_versions": [], "entities": [], "entities_versions": []},
        "agents": [],
        "persist": persist,
        "expires_at": None,
    }


def run_json(run_id: str | None = None, status: str = "en_cours") -> dict[str, Any]:
    return {
        "id": run_id or str(uuid.uuid4()),
        "name": "Run",
        "analyse_id": None,
        "created_at": NOW,
        "status": status,
        "started_at": NOW,
        "ended_at": None,
        "execution_steps": [],
        "documents": [],
        "persist": False,
        "ttl_hours": 24,
        "expires_at": None,
    }


@pytest.fixture
def make_client() -> Callable[..., tuple[EphemeralClient, list[httpx.Request]]]:
    def factory(
        handler: Callable[[httpx.Request], httpx.Response], **kwargs: Any
    ) -> tuple[EphemeralClient, list[httpx.Request]]:
        seen: list[httpx.Request] = []

        def recording(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return handler(request)

        kwargs.setdefault("api_token", "ddd_tok")
        kwargs.setdefault("backoff_factor", 0)
        return EphemeralClient("https://api.test", transport=httpx.MockTransport(recording), **kwargs), seen

    return factory
