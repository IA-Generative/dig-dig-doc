"""Les modèles éphémères doivent refléter les schémas du backend (../openapi.json)."""

from __future__ import annotations

import pytest
from contract import check
from pydantic import BaseModel

from digdigdoc_ephemeral import models as m

CASES: list[tuple[type[BaseModel], str]] = [
    (m.EphemeralAnalysisConfig, "EphemeralAnalyseCreate"),
    (m.EphemeralAnalyseCreated, "EphemeralAnalyseCreated"),
    (m.EphemeralRunCreated, "EphemeralRunCreated"),
    (m.EphemeralAnalyse, "EphemeralAnalyseOut"),
    (m.EphemeralRun, "EphemeralRunOut"),
]


@pytest.mark.parametrize(("model", "schema"), CASES, ids=lambda v: v if isinstance(v, str) else v.__name__)
def test_model_matches_backend_schema(model: type[BaseModel], schema: str) -> None:
    assert check(model, schema) == []
