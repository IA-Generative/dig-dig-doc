"""Tests pour les tâches de classification et d'extraction."""

import json

import httpx

from app import api_client
from app.llm import ClassificationResult, EntityValue, ExtractionResult, LabelPrediction
from app.storage import storage as storage_instance
from app.tasks import classification as classification_mod
from app.tasks import extraction as extraction_mod
from app.tasks.classification import classify_dossier
from app.tasks.extraction import extract_dossier_entities


def _step_complete_response(step_id: str, kind: str) -> dict:
    return {
        "id": step_id,
        "kind": kind,
        "label": "",
        "status": "terminé",
        "started_at": "",
        "ended_at": "",
        "output": "",
        "logs": [],
    }


def _log_response() -> dict:
    return {"id": "log-1", "level": "info", "message": "ok", "created_at": ""}


def _make_dossier_response() -> dict:
    return {
        "id": "dossier-1",
        "analyse_id": "analyse-1",
        "status": "en_cours",
        "execution_steps": [
            {
                "id": "step-classif",
                "kind": "classification",
                "label": "Classification",
                "status": "en_cours",
            },
            {
                "id": "step-extract",
                "kind": "extraction",
                "label": "Extraction",
                "status": "en_cours",
            },
        ],
        "documents": [
            {
                "id": "doc-1",
                "name": "cni.pdf",
                "s3_key": "dossiers/x/cni.pdf",
                "mimetype": "application/pdf",
                "text_extraction_status": "terminé",
                "pages": [
                    {
                        "id": "page-1",
                        "page_number": 1,
                        "content": "Carte Nationale d'Identité\nNom: Dupont\nPrénom: Jean",
                        "screenshot_key": "screenshots/doc-1/page-1.png",
                    },
                    {
                        "id": "page-2",
                        "page_number": 2,
                        "content": "Adresse: 123 rue de Paris",
                        "screenshot_key": None,
                    },
                ],
            }
        ],
    }


def _make_analyse_response() -> dict:
    return {
        "id": "analyse-1",
        "classification": {
            "prompt": "Classifie ce document.",
            "labels": [
                {
                    "id": "label-cni",
                    "name": "CNI",
                    "definition": "Carte Nationale d'Identité",
                },
                {
                    "id": "label-passport",
                    "name": "Passeport",
                    "definition": "Passeport officiel",
                },
            ],
        },
        "extraction": {
            "prompt": "Extrais les entités.",
            "entities": [
                {
                    "id": "entity-nom",
                    "name": "nom",
                    "definition": "Nom de famille",
                    "type": "texte",
                },
                {
                    "id": "entity-adresse",
                    "name": "adresse",
                    "definition": "Adresse postale",
                    "type": "texte",
                },
            ],
        },
    }


def test_classify_dossier_deposits_label_predictions(monkeypatch) -> None:
    calls: list[tuple[str, str]] = []
    prediction_bodies: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        if request.url.path.endswith("/dossiers/dossier-1"):
            return httpx.Response(200, json=_make_dossier_response())
        if request.url.path.endswith("/analyses/analyse-1"):
            return httpx.Response(200, json=_make_analyse_response())
        if request.url.path.endswith("/logs"):
            return httpx.Response(200, json=_log_response())
        if request.url.path.endswith("/complete"):
            return httpx.Response(
                200, json=_step_complete_response("step-classif", "classification")
            )
        if request.url.path.endswith("/predictions"):
            prediction_bodies.append(json.loads(request.content))
            return httpx.Response(201, json={"id": "pred-1", **prediction_bodies[-1]})
        return httpx.Response(404)

    monkeypatch.setattr(
        api_client,
        "get_client",
        lambda: httpx.Client(
            base_url="http://backend/api/internal",
            transport=httpx.MockTransport(handler),
        ),
    )
    monkeypatch.setattr(storage_instance, "get_object", lambda key: b"fake-png-bytes")
    monkeypatch.setattr(
        classification_mod.llm,
        "describe_page_image",
        lambda image_bytes: "Photo d'identité visible, type CNI",
    )
    monkeypatch.setattr(
        classification_mod.llm,
        "classify_page",
        lambda **kwargs: ClassificationResult(
            prediction=LabelPrediction(
                label_name="CNI", confidence=0.95, reasoning="Photo visible"
            )
        ),
    )

    classify_dossier.run("dossier-1")

    # Two pages classified
    assert len(prediction_bodies) == 2
    assert prediction_bodies[0]["kind"] == "label"
    assert prediction_bodies[0]["name"] == "CNI"
    assert prediction_bodies[0]["label_definition_id"] == "label-cni"
    assert prediction_bodies[0]["confidence"] == 0.95
    # Step completed
    assert any(path.endswith("/complete") for _, path in calls)


def test_classify_dossier_handles_no_labels(monkeypatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/dossiers/dossier-1"):
            return httpx.Response(200, json=_make_dossier_response())
        if request.url.path.endswith("/analyses/analyse-1"):
            resp = _make_analyse_response()
            resp["classification"]["labels"] = []
            return httpx.Response(200, json=resp)
        if request.url.path.endswith("/logs"):
            return httpx.Response(200, json=_log_response())
        if request.url.path.endswith("/complete"):
            return httpx.Response(
                200, json=_step_complete_response("step-classif", "classification")
            )
        return httpx.Response(404)

    monkeypatch.setattr(
        api_client,
        "get_client",
        lambda: httpx.Client(
            base_url="http://backend/api/internal",
            transport=httpx.MockTransport(handler),
        ),
    )

    classify_dossier.run("dossier-1")
    # No predictions deposited when no labels defined


def test_extract_dossier_entities_deposits_entity_predictions(monkeypatch) -> None:
    calls: list[tuple[str, str]] = []
    prediction_bodies: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        if request.url.path.endswith("/dossiers/dossier-1"):
            return httpx.Response(200, json=_make_dossier_response())
        if request.url.path.endswith("/analyses/analyse-1"):
            return httpx.Response(200, json=_make_analyse_response())
        if request.url.path.endswith("/logs"):
            return httpx.Response(200, json=_log_response())
        if request.url.path.endswith("/complete"):
            return httpx.Response(
                200, json=_step_complete_response("step-extract", "extraction")
            )
        if request.url.path.endswith("/predictions"):
            prediction_bodies.append(json.loads(request.content))
            return httpx.Response(201, json={"id": "pred-1", **prediction_bodies[-1]})
        return httpx.Response(404)

    monkeypatch.setattr(
        api_client,
        "get_client",
        lambda: httpx.Client(
            base_url="http://backend/api/internal",
            transport=httpx.MockTransport(handler),
        ),
    )
    monkeypatch.setattr(
        extraction_mod.llm,
        "extract_entities_batch",
        lambda **kwargs: ExtractionResult(
            entities=[
                EntityValue(
                    entity_name="nom", value="Dupont", confidence=0.95, page_numbers=[1]
                ),
                EntityValue(
                    entity_name="adresse",
                    value="123 rue de Paris",
                    confidence=0.88,
                    page_numbers=[2],
                ),
            ]
        ),
    )

    extract_dossier_entities.run("dossier-1")

    assert len(prediction_bodies) == 2
    assert prediction_bodies[0]["kind"] == "entity"
    assert prediction_bodies[0]["name"] == "nom"
    assert prediction_bodies[0]["value"] == "Dupont"
    assert prediction_bodies[0]["entity_definition_id"] == "entity-nom"
    assert prediction_bodies[0]["page_ids"] == ["page-1"]
    assert prediction_bodies[1]["name"] == "adresse"
    assert prediction_bodies[1]["page_ids"] == ["page-2"]


def test_extract_dossier_entities_handles_no_entities(monkeypatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/dossiers/dossier-1"):
            return httpx.Response(200, json=_make_dossier_response())
        if request.url.path.endswith("/analyses/analyse-1"):
            resp = _make_analyse_response()
            resp["extraction"]["entities"] = []
            return httpx.Response(200, json=resp)
        if request.url.path.endswith("/logs"):
            return httpx.Response(200, json=_log_response())
        if request.url.path.endswith("/complete"):
            return httpx.Response(
                200, json=_step_complete_response("step-extract", "extraction")
            )
        return httpx.Response(404)

    monkeypatch.setattr(
        api_client,
        "get_client",
        lambda: httpx.Client(
            base_url="http://backend/api/internal",
            transport=httpx.MockTransport(handler),
        ),
    )

    extract_dossier_entities.run("dossier-1")
    # No predictions deposited when no entities defined
