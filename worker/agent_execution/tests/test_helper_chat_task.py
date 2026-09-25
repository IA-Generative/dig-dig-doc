"""Tests pour la tâche de réponse de l'agent helper (issue #50)."""

import json

import httpx

from app import api_client
from app.tasks import helper_chat as helper_chat_mod
from app.tasks.helper_chat import run_helper_chat


def _conversation_response() -> dict:
    return {
        "id": "conv-1",
        "created_by": "dev-user",
        "messages": [{"id": "m1", "role": "user", "content": "Trouve-moi le dossier CNI"}],
    }


def test_run_helper_chat_deposits_answer_with_resources(monkeypatch) -> None:
    calls: list[tuple[str, str]] = []
    events: list[dict] = []
    deposited: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        if request.url.path.endswith("/agent-conversations/conv-1") and request.method == "GET":
            return httpx.Response(200, json=_conversation_response())
        if request.url.path.endswith("/chat-events"):
            events.append(json.loads(request.content))
            return httpx.Response(201, json={"id": "evt", "agent_conversation_id": "conv-1", **events[-1]})
        if request.url.path.endswith("/agent-conversations/conv-1/messages"):
            deposited.update(json.loads(request.content))
            return httpx.Response(200, json={"ok": True})
        return httpx.Response(404)

    monkeypatch.setattr(
        api_client,
        "get_client",
        lambda: httpx.Client(
            base_url="http://backend/api/internal",
            transport=httpx.MockTransport(handler),
        ),
    )

    from app.helper_tools import ConsultedResource

    def fake_graph(conversation_history, tools, on_event=None, model=None):
        assert conversation_history == [{"role": "user", "content": "Trouve-moi le dossier CNI"}]
        if on_event:
            on_event("tool_call", {"tool_name": "search_dossiers", "arguments": {}})
        return "Voici le dossier CNI.", [ConsultedResource(dossier_id="d1", excerpt="Dossier CNI")]

    monkeypatch.setattr(helper_chat_mod, "run_helper_chat_graph", fake_graph)

    run_helper_chat.run("conv-1")

    assert deposited["content"] == "Voici le dossier CNI."
    assert deposited["sources"] == [{"dossier_id": "d1", "analyse_id": None, "excerpt": "Dossier CNI"}]
    kinds = [e["kind"] for e in events]
    assert kinds == ["tool_call", "done"]


def test_run_helper_chat_emits_error_event_and_reraises(monkeypatch) -> None:
    events: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/agent-conversations/conv-1") and request.method == "GET":
            return httpx.Response(200, json=_conversation_response())
        if request.url.path.endswith("/chat-events"):
            events.append(json.loads(request.content))
            return httpx.Response(201, json={"id": "evt", "agent_conversation_id": "conv-1", **events[-1]})
        return httpx.Response(404)

    monkeypatch.setattr(
        api_client,
        "get_client",
        lambda: httpx.Client(
            base_url="http://backend/api/internal",
            transport=httpx.MockTransport(handler),
        ),
    )

    def failing_graph(conversation_history, tools, on_event=None, model=None):
        raise RuntimeError("boom")

    monkeypatch.setattr(helper_chat_mod, "run_helper_chat_graph", failing_graph)

    try:
        run_helper_chat.run("conv-1")
        raised = False
    except RuntimeError:
        raised = True

    assert raised
    assert events[-1]["kind"] == "error"
    assert events[-1]["data"]["message"] == "boom"
