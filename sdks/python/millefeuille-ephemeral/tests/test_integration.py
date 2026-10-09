"""Tests d'intégration : `MILLEFEUILLE_BASE_URL=... MILLEFEUILLE_API_TOKEN=... uv run pytest -m integration`."""

from __future__ import annotations

import os

import pytest

from millefeuille_ephemeral import EphemeralAnalysisConfig, EphemeralClient

pytestmark = pytest.mark.integration

BASE_URL = os.environ.get("MILLEFEUILLE_BASE_URL")
API_TOKEN = os.environ.get("MILLEFEUILLE_API_TOKEN")


@pytest.mark.skipif(not (BASE_URL and API_TOKEN), reason="MILLEFEUILLE_BASE_URL / MILLEFEUILLE_API_TOKEN non définis")
def test_analyze_roundtrip() -> None:
    assert BASE_URL and API_TOKEN
    with EphemeralClient(BASE_URL, api_token=API_TOKEN) as client:
        result = client.analyze(
            [("hello.txt", b"Bonjour")],
            EphemeralAnalysisConfig(name="sdk-integration", classification_prompt="Classe le document"),
            ttl_hours=1,
            timeout=600,
            cleanup=True,
        )
    assert result.status.is_terminal
