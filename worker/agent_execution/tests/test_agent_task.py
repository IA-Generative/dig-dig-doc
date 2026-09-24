"""Tests pour la tâche d'exécution des agents."""

import json

import httpx

from app import api_client
from app.tasks import agent as agent_mod
from app.tasks.agent import run_agents


def _make_dossier_response() -> dict:
    return {
        "id": "dossier-1",
        "analyse_id": "analyse-1",
        "status": "en_cours",
        "execution_steps": [
            {
                "id": "step-classif",
                "kind": "classification",
                "label": "Classification documentaire",
                "status": "terminé",
            },
            {
                "id": "step-extract",
                "kind": "extraction",
                "label": "Extraction d'entités nommées",
                "status": "terminé",
            },
            {
                "id": "step-agent-1",
                "kind": "agent",
                "label": "Vérification de cohérence",
                "status": "en_cours",
            },
        ],
        "documents": [
            {
                "id": "doc-1",
                "name": "CNI.pdf",
                "s3_key": "docs/doc-1.pdf",
                "mimetype": "application/pdf",
                "text_extraction_status": "terminé",
                "pages": [
                    {
                        "id": "page-1",
                        "page_number": 1,
                        "content": "Carte nationale d'identité. Nom: Dupont.",
                        "screenshot_key": "screens/page-1.png",
                        "predictions": [
                            {
                                "kind": "label",
                                "name": "CNI",
                                "value": "CNI",
                                "confidence": 0.95,
                            },
                            {
                                "kind": "entity",
                                "name": "nom",
                                "value": "Dupont",
                                "confidence": 0.92,
                            },
                        ],
                    },
                ],
            },
        ],
    }


def _make_analyse_response() -> dict:
    return {
        "id": "analyse-1",
        "classification": {
            "prompt": "Classifie les documents.",
            "labels": [
                {"id": "label-cni", "name": "CNI", "definition": "Carte d'identité"},
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
            ],
        },
        "agents": [
            {
                "id": "agent-1",
                "name": "Vérification de cohérence",
                "prompt": "Vérifie la cohérence des documents du dossier.",
                "tools": ["lecture_document", "verification_coherence"],
                "output": True,
                "model": None,
            },
        ],
    }


def _step_complete_response(step_id: str) -> dict:
    return {
        "id": step_id,
        "kind": "agent",
        "label": "",
        "status": "terminé",
        "started_at": "",
        "ended_at": "",
        "output": "",
        "logs": [],
    }


def _log_response() -> dict:
    return {"id": "log-1", "level": "info", "message": "ok", "created_at": ""}


def test_run_agents_executes_and_completes(monkeypatch) -> None:
    calls: list[tuple[str, str]] = []
    complete_bodies: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        if request.url.path.endswith("/dossiers/dossier-1"):
            return httpx.Response(200, json=_make_dossier_response())
        if request.url.path.endswith("/analyses/analyse-1"):
            return httpx.Response(200, json=_make_analyse_response())
        if request.url.path.endswith("/logs"):
            return httpx.Response(200, json=_log_response())
        if request.url.path.endswith("/complete"):
            body = json.loads(request.content)
            complete_bodies.append(body)
            return httpx.Response(200, json=_step_complete_response("step-agent-1"))
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
        agent_mod,
        "run_agent",
        lambda agent_prompt, tools, model=None: "Synthèse: dossier cohérent.",
    )
    # Skip the wait loop — steps are already "terminé" in the mock response
    monkeypatch.setattr(agent_mod, "_wait_for_steps", lambda client, dossier, kinds: {})

    run_agents.run("dossier-1")

    # Agent step should be completed with the synthesis
    assert len(complete_bodies) == 1
    assert complete_bodies[0]["status"] == "terminé"
    assert complete_bodies[0]["output"] == "Synthèse: dossier cohérent."


def test_run_agents_no_agents_defined(monkeypatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/dossiers/dossier-1"):
            return httpx.Response(200, json=_make_dossier_response())
        if request.url.path.endswith("/analyses/analyse-1"):
            resp = _make_analyse_response()
            resp["agents"] = []
            return httpx.Response(200, json=resp)
        return httpx.Response(404)

    monkeypatch.setattr(
        api_client,
        "get_client",
        lambda: httpx.Client(
            base_url="http://backend/api/internal",
            transport=httpx.MockTransport(handler),
        ),
    )

    run_agents.run("dossier-1")
    # No agents → no complete calls, no errors


def test_run_agents_agent_failure_completes_with_echec(monkeypatch) -> None:
    complete_bodies: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/dossiers/dossier-1"):
            return httpx.Response(200, json=_make_dossier_response())
        if request.url.path.endswith("/analyses/analyse-1"):
            return httpx.Response(200, json=_make_analyse_response())
        if request.url.path.endswith("/logs"):
            return httpx.Response(200, json=_log_response())
        if request.url.path.endswith("/complete"):
            body = json.loads(request.content)
            complete_bodies.append(body)
            return httpx.Response(200, json=_step_complete_response("step-agent-1"))
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
        agent_mod,
        "run_agent",
        lambda agent_prompt, tools, model=None: (_ for _ in ()).throw(RuntimeError("LLM error")),
    )
    monkeypatch.setattr(agent_mod, "_wait_for_steps", lambda client, dossier, kinds: {})

    run_agents.run("dossier-1")

    assert len(complete_bodies) == 1
    assert complete_bodies[0]["status"] == "échec"
    assert "LLM error" in complete_bodies[0]["output"]
