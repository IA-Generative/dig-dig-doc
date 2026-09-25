"""Tests pour la tâche de suggestion d'analyse (issue #54)."""

import json

import httpx

from app import api_client
from app.llm import AnalyseSuggestion, SuggestionResult
from app.tasks import suggestion as suggestion_mod
from app.tasks.suggestion import suggest_dossier_analyse


def _make_dossier_response(*, with_summary: bool = True, with_documents: bool = True) -> dict:
    dossier = {
        "id": "dossier-1",
        "analyse_id": None,
        "status": "en_attente",
        "suggestion_status": "en_attente",
        "execution_steps": [],
        "documents": [],
        "summary": None,
    }
    if with_summary:
        dossier["summary"] = {"content": "Dossier contenant une CNI et un justificatif de domicile."}
    if with_documents:
        dossier["documents"] = [
            {
                "id": "doc-1",
                "name": "cni.pdf",
                "s3_key": "dossiers/x/cni.pdf",
                "mimetype": "application/pdf",
                "pages": [
                    {
                        "id": "page-1",
                        "page_number": 1,
                        "content": "Carte Nationale d'Identité\nNom: Dupont",
                    },
                ],
                "summary": {"content": "CNI de Dupont"},
            },
            {
                "id": "doc-2",
                "name": "facture.pdf",
                "s3_key": "dossiers/x/facture.pdf",
                "mimetype": "application/pdf",
                "pages": [
                    {
                        "id": "page-2",
                        "page_number": 1,
                        "content": "Facture d'électricité, 123 rue de Paris",
                    },
                ],
                "summary": {"content": "Facture EDF à l'adresse du domicile"},
            },
        ]
    return dossier


def _make_analyses_response() -> dict:
    return {
        "items": [
            {"id": "analyse-cni", "name": "Vérification CNI"},
            {"id": "analyse-domicile", "name": "Justificatif de domicile"},
            {"id": "analyse-fiscal", "name": "Analyse fiscale"},
        ],
        "total": 3,
        "page": 1,
        "page_size": 100,
    }


def test_suggest_dossier_analyse_deposits_suggestions(monkeypatch) -> None:
    """La tâche récupère le dossier, liste les analyses, appelle le LLM et
    dépose les suggestions enrichies avec les noms d'analyse."""
    deposited: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "PUT" and path.endswith("/suggestion-status"):
            return httpx.Response(200, json={"suggestion_status": json.loads(request.content)["status"]})
        if path.endswith("/dossiers/dossier-1"):
            return httpx.Response(200, json=_make_dossier_response())
        if path.endswith("/analyses"):
            return httpx.Response(200, json=_make_analyses_response())
        if request.method == "POST" and path.endswith("/suggestions"):
            deposited.append(json.loads(request.content))
            return httpx.Response(
                200,
                json={
                    "suggestion_status": "terminé",
                    "suggested_analyses": deposited[-1]["suggestions"],
                },
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

    fake_result = SuggestionResult(
        suggestions=[
            AnalyseSuggestion(analyse_id="analyse-cni", score=0.95, rationale="CNI présente"),
            AnalyseSuggestion(
                analyse_id="analyse-domicile",
                score=0.80,
                rationale="Justificatif de domicile",
            ),
        ]
    )
    monkeypatch.setattr(suggestion_mod, "suggest_analyses", lambda **kwargs: fake_result)

    suggest_dossier_analyse.run("dossier-1")

    assert len(deposited) == 1
    suggestions = deposited[0]["suggestions"]
    assert len(suggestions) == 2
    assert suggestions[0]["analyse_id"] == "analyse-cni"
    assert suggestions[0]["name"] == "Vérification CNI"
    assert suggestions[0]["score"] == 0.95
    assert suggestions[0]["rationale"] == "CNI présente"
    assert suggestions[1]["analyse_id"] == "analyse-domicile"
    assert suggestions[1]["name"] == "Justificatif de domicile"


def test_suggest_dossier_analyse_filters_unknown_analyses(monkeypatch) -> None:
    """Les suggestions référençant des analyses inconnues sont filtrées."""
    deposited: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "PUT" and path.endswith("/suggestion-status"):
            return httpx.Response(200, json={"suggestion_status": json.loads(request.content)["status"]})
        if path.endswith("/dossiers/dossier-1"):
            return httpx.Response(200, json=_make_dossier_response())
        if path.endswith("/analyses"):
            return httpx.Response(200, json=_make_analyses_response())
        if request.method == "POST" and path.endswith("/suggestions"):
            deposited.append(json.loads(request.content))
            return httpx.Response(200, json={"suggestion_status": "terminé"})
        return httpx.Response(404)

    monkeypatch.setattr(
        api_client,
        "get_client",
        lambda: httpx.Client(
            base_url="http://backend/api/internal",
            transport=httpx.MockTransport(handler),
        ),
    )

    fake_result = SuggestionResult(
        suggestions=[
            AnalyseSuggestion(analyse_id="analyse-cni", score=0.90, rationale="OK"),
            AnalyseSuggestion(analyse_id="unknown-id", score=0.50, rationale="Inconnu"),
        ]
    )
    monkeypatch.setattr(suggestion_mod, "suggest_analyses", lambda **kwargs: fake_result)

    suggest_dossier_analyse.run("dossier-1")

    suggestions = deposited[0]["suggestions"]
    assert len(suggestions) == 1
    assert suggestions[0]["analyse_id"] == "analyse-cni"


def test_suggest_dossier_analyse_empty_content_deposits_empty(monkeypatch) -> None:
    """Si le dossier n'a ni résumé ni contenu, on dépose une liste vide."""
    deposited: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "PUT" and path.endswith("/suggestion-status"):
            return httpx.Response(200, json={"suggestion_status": json.loads(request.content)["status"]})
        if path.endswith("/dossiers/dossier-1"):
            return httpx.Response(
                200,
                json=_make_dossier_response(with_summary=False, with_documents=False),
            )
        if request.method == "POST" and path.endswith("/suggestions"):
            deposited.append(json.loads(request.content))
            return httpx.Response(200, json={"suggestion_status": "terminé"})
        return httpx.Response(404)

    monkeypatch.setattr(
        api_client,
        "get_client",
        lambda: httpx.Client(
            base_url="http://backend/api/internal",
            transport=httpx.MockTransport(handler),
        ),
    )

    # Le LLM ne doit pas être appelé si le contenu est vide
    monkeypatch.setattr(
        suggestion_mod,
        "suggest_analyses",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("LLM should not be called")),
    )

    suggest_dossier_analyse.run("dossier-1")

    assert len(deposited) == 1
    assert deposited[0]["suggestions"] == []


def test_suggest_dossier_analyse_no_analyses_deposits_empty(monkeypatch) -> None:
    """Si aucune analyse n'est disponible, on dépose une liste vide."""
    deposited: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "PUT" and path.endswith("/suggestion-status"):
            return httpx.Response(200, json={"suggestion_status": json.loads(request.content)["status"]})
        if path.endswith("/dossiers/dossier-1"):
            return httpx.Response(200, json=_make_dossier_response())
        if path.endswith("/analyses"):
            return httpx.Response(200, json={"items": [], "total": 0, "page": 1, "page_size": 100})
        if request.method == "POST" and path.endswith("/suggestions"):
            deposited.append(json.loads(request.content))
            return httpx.Response(200, json={"suggestion_status": "terminé"})
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
        suggestion_mod,
        "suggest_analyses",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("LLM should not be called")),
    )

    suggest_dossier_analyse.run("dossier-1")

    assert len(deposited) == 1
    assert deposited[0]["suggestions"] == []


def test_suggest_dossier_analyse_sets_echec_on_error(monkeypatch) -> None:
    """Si une erreur se produit, le statut est mis à échec avec l'erreur."""
    status_updates: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "PUT" and path.endswith("/suggestion-status"):
            body = json.loads(request.content)
            status_updates.append(body)
            return httpx.Response(200, json={"suggestion_status": body["status"]})
        if path.endswith("/dossiers/dossier-1"):
            return httpx.Response(200, json=_make_dossier_response())
        if path.endswith("/analyses"):
            return httpx.Response(200, json=_make_analyses_response())
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
        suggestion_mod,
        "suggest_analyses",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("LLM API down")),
    )

    try:
        suggest_dossier_analyse.run("dossier-1")
    except RuntimeError:
        pass

    # First update: en_cours, second: échec
    assert len(status_updates) >= 2
    assert status_updates[0]["status"] == "en_cours"
    assert status_updates[-1]["status"] == "échec"
    assert "LLM API down" in status_updates[-1]["error"]
