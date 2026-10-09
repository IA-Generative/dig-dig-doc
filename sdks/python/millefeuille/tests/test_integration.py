"""Tests d'intégration : `MILLEFEUILLE_BASE_URL=... MILLEFEUILLE_BEARER_TOKEN=... uv run pytest -m integration`."""

from __future__ import annotations

import os

import pytest

from millefeuille import MilleFeuilleClient

pytestmark = pytest.mark.integration

BASE_URL = os.environ.get("MILLEFEUILLE_BASE_URL")
BEARER_TOKEN = os.environ.get("MILLEFEUILLE_BEARER_TOKEN")


@pytest.mark.skipif(not (BASE_URL and BEARER_TOKEN), reason="MILLEFEUILLE_BASE_URL / MILLEFEUILLE_BEARER_TOKEN non définis")
def test_analyse_and_dossier_lifecycle() -> None:
    assert BASE_URL and BEARER_TOKEN
    with MilleFeuilleClient(BASE_URL, bearer_token=BEARER_TOKEN) as client:
        analyse = client.analyses.create("sdk-integration", "Test d'intégration du SDK")
        dossier = client.dossiers.create("sdk-integration", analyse_id=analyse.id)
        try:
            assert client.dossiers.get(dossier.id).analyse_id == analyse.id
        finally:
            client.dossiers.delete(dossier.id)
            client.analyses.delete(analyse.id)
