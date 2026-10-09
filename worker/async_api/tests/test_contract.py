import json
from pathlib import Path

from mic_worker.manifeste import charger

from src.messages import AnalyzeRequest, FileRef

CONTRAT = Path(__file__).resolve().parents[1] / "contrat.json"


def test_manifest_is_valid_for_mic_worker() -> None:
    manifeste = charger(CONTRAT)
    assert manifeste.nom == "mille-feuille"
    assert str(manifeste.classe) in ("long", "ClasseDeService.LONG") or manifeste.classe.value == "long"


def test_input_schema_matches_the_request_model() -> None:
    schema = json.loads(CONTRAT.read_text())["entree"]
    assert set(schema["properties"]) == set(AnalyzeRequest.model_fields)
    assert set(schema["required"]) == {"files"}
    file_schema = schema["properties"]["files"]["items"]
    assert set(file_schema["properties"]) == set(FileRef.model_fields)
    assert schema["properties"]["ttl_hours"]["maximum"] == 17520


def test_analysis_schema_matches_the_sdk_config() -> None:
    from millefeuille_ephemeral import EphemeralAnalysisConfig

    schema = json.loads(CONTRAT.read_text())["entree"]["properties"]["analysis"]
    assert set(schema["properties"]) == set(EphemeralAnalysisConfig.model_fields)


def test_display_name_defaults_to_last_key_segment() -> None:
    assert FileRef(file_id="astree/a1/cni.pdf").display_name == "cni.pdf"
    assert FileRef(file_id="astree/a1/cni.pdf", name="Ma CNI").display_name == "Ma CNI"
