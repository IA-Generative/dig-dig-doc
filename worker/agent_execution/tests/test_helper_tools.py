"""Tests pour les outils de l'agent helper (issue #50)."""

import json

import httpx

from app.helper_tools import HelperTools


def _client(handler) -> httpx.Client:
    return httpx.Client(base_url="http://backend/api/internal", transport=httpx.MockTransport(handler))


def test_search_analyses_formats_results_and_records_resources() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/agent/analyses")
        assert request.url.params["q"] == "CNI"
        return httpx.Response(
            200,
            json={
                "items": [
                    {"id": "a1", "name": "Analyse CNI", "description": "desc", "agent_count": 2, "created_at": ""}
                ],
                "total": 1,
                "page": 1,
                "page_size": 20,
                "pages": 1,
            },
        )

    tools = HelperTools(_client(handler))
    result = tools.search_analyses("CNI")

    assert "Analyse CNI" in result
    assert "a1" in result
    resources = tools.consulted_resources()
    assert len(resources) == 1
    assert resources[0].analyse_id == "a1"


def test_get_analysis_not_found_returns_error_message() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": "Analyse introuvable"})

    tools = HelperTools(_client(handler))
    result = tools.get_analysis("missing")

    assert result == "Erreur : Analyse introuvable"
    assert tools.consulted_resources() == []


def test_create_dossier_then_run_and_get_results() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(f"{request.method} {request.url.path}")
        if request.url.path.endswith("/agent/dossiers") and request.method == "POST":
            body = json.loads(request.content)
            assert body == {"name": "Dossier CNI", "analyse_id": "a1"}
            return httpx.Response(
                201,
                json={
                    "id": "d1",
                    "name": "Dossier CNI",
                    "analyse_id": "a1",
                    "status": "brouillon",
                    "documents": [],
                    "execution_steps": [],
                },
            )
        if request.url.path.endswith("/agent/dossiers/d1/launch"):
            return httpx.Response(
                200,
                json={
                    "id": "d1",
                    "name": "Dossier CNI",
                    "analyse_id": "a1",
                    "status": "en_cours",
                    "documents": [],
                    "execution_steps": [],
                },
            )
        if request.url.path.endswith("/agent/dossiers/d1"):
            return httpx.Response(
                200,
                json={
                    "id": "d1",
                    "name": "Dossier CNI",
                    "analyse_id": "a1",
                    "status": "termine",
                    "documents": [{"id": "doc-1"}],
                    "execution_steps": [
                        {"kind": "agent", "label": "Synthèse", "output": "Cohérent.", "status": "termine"}
                    ],
                },
            )
        return httpx.Response(404)

    tools = HelperTools(_client(handler))

    created = tools.create_dossier("Dossier CNI", "a1")
    assert "Dossier CNI" in created
    assert "d1" in created

    launched = tools.run_dossier("d1")
    assert "en_cours" in launched

    results = tools.get_dossier_results("d1")
    assert "termine" in results
    assert "Cohérent." in results

    resources = tools.consulted_resources()
    assert {r.dossier_id for r in resources} == {"d1"}


def test_tool_definitions_cover_every_dispatchable_tool() -> None:
    tools = HelperTools(_client(lambda request: httpx.Response(404)))
    defined = {d["function"]["name"] for d in tools.tool_definitions()}
    assert defined == {
        "list_analyses",
        "search_analyses",
        "get_analysis",
        "create_analysis",
        "list_dossiers",
        "get_dossier",
        "create_dossier",
        "run_dossier",
        "get_dossier_results",
    }


def test_dispatch_tool_unknown_name() -> None:
    tools = HelperTools(_client(lambda request: httpx.Response(404)))
    assert tools.dispatch_tool("not_a_tool", {}) == "Outil 'not_a_tool' inconnu."
