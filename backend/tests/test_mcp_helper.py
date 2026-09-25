import base64
import json
import uuid

import httpx2
from fastapi.testclient import TestClient
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client

from app.db import async_session_factory
from app.main import app
from app.models.agent_conversation import AgentMessageRole
from app.repositories.agent_conversation_repository import AgentConversationRepository


def _mcp_session(token: str):
    """Un vrai client MCP (SDK officiel), même pattern que test_mcp.py pour
    le serveur éphémère : exerce le protocole complet (handshake, session
    Streamable HTTP, JSON-RPC) plutôt que d'appeler les tools directement."""
    transport = httpx2.ASGITransport(app=app)
    http_client = httpx2.AsyncClient(
        transport=transport, base_url="http://testserver", headers={"Authorization": f"Bearer {token}"}
    )
    return streamable_http_client(url="http://testserver/mcp/helper/", http_client=http_client)


def _call_tool_json(result) -> dict:
    assert not result.is_error, result.content
    return json.loads(result.content[0].text)


def test_mcp_helper_full_cycle(client: TestClient) -> None:
    token = client.post("/api/app-tokens", json={"name": "mcp-helper-test"}).json()["token"]

    async def run() -> None:
        async with _mcp_session(token) as (read, write):
            async with ClientSession(read, write) as session:
                init = await session.initialize()
                assert init.server_info.name == "dig-dig-doc-helper"

                tools = await session.list_tools()
                assert {t.name for t in tools.tools} == {
                    "create_agent_conversation",
                    "list_analyses",
                    "search_analyses",
                    "get_analysis",
                    "create_analysis",
                    "create_dossier",
                    "add_dossier_files",
                    "list_dossiers",
                    "get_dossier",
                    "run_dossier",
                    "get_dossier_results",
                }

                conv = _call_tool_json(await session.call_tool("create_agent_conversation", {"title": "Test MCP"}))
                conversation_id = conv["conversation_id"]

                created = _call_tool_json(
                    await session.call_tool(
                        "create_analysis",
                        {"name": "Analyse MCP helper", "description": "desc", "conversation_id": conversation_id},
                    )
                )
                analyse_id = created["id"]
                assert created["name"] == "Analyse MCP helper"

                fetched = _call_tool_json(await session.call_tool("get_analysis", {"analyse_id": analyse_id}))
                assert fetched["id"] == analyse_id

                found = _call_tool_json(await session.call_tool("search_analyses", {"q": "MCP helper"}))
                assert found["total"] >= 1
                assert any(item["id"] == analyse_id for item in found["items"])

                listed = _call_tool_json(await session.call_tool("list_analyses", {"page_size": 100}))
                assert any(item["id"] == analyse_id for item in listed["items"])

                dossier = _call_tool_json(
                    await session.call_tool(
                        "create_dossier",
                        {"name": "Dossier MCP helper", "analyse_id": analyse_id, "conversation_id": conversation_id},
                    )
                )
                dossier_id = dossier["id"]
                assert dossier["documents"] == []

                with_files = _call_tool_json(
                    await session.call_tool(
                        "add_dossier_files",
                        {
                            "dossier_id": dossier_id,
                            "files": [
                                {
                                    "name": "cni.pdf",
                                    "content_base64": base64.b64encode(b"fake-bytes").decode(),
                                    "mimetype": "application/pdf",
                                }
                            ],
                        },
                    )
                )
                assert len(with_files["documents"]) == 1

                listed_dossiers = _call_tool_json(await session.call_tool("list_dossiers", {"page_size": 100}))
                assert any(d["id"] == dossier_id for d in listed_dossiers["items"])

                launched = _call_tool_json(
                    await session.call_tool(
                        "run_dossier", {"dossier_id": dossier_id, "conversation_id": conversation_id}
                    )
                )
                assert launched["status"] == "en_cours"

                results = _call_tool_json(await session.call_tool("get_dossier_results", {"dossier_id": dossier_id}))
                assert results["id"] == dossier_id

                not_found = _call_tool_json(await session.call_tool("get_dossier", {"dossier_id": str(uuid.uuid4())}))
                assert not_found == {"error": "Dossier introuvable", "status_code": 404}

        # Vérifie la journalisation : les 3 appels passés avec conversation_id
        # (create_analysis, create_dossier, run_dossier) ont chacun déposé un
        # tool_call + un tool_result.
        async with async_session_factory() as db:
            conversation = await AgentConversationRepository(db).get(uuid.UUID(conversation_id))
            assert conversation is not None
            assert conversation.title == "Test MCP"
            tool_names = [m.tool_name for m in conversation.messages]
            assert tool_names.count("create_analysis") == 2  # tool_call + tool_result
            assert tool_names.count("create_dossier") == 2
            assert tool_names.count("run_dossier") == 2
            roles = {m.role for m in conversation.messages}
            assert roles == {AgentMessageRole.TOOL_CALL, AgentMessageRole.TOOL_RESULT}

    client.portal.call(run)


def test_mcp_helper_requires_bearer_token(client: TestClient) -> None:
    transport = httpx2.ASGITransport(app=app)

    async def run() -> None:
        http_client = httpx2.AsyncClient(transport=transport, base_url="http://testserver")
        response = await http_client.post(
            "/mcp/helper/",
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            headers={"Accept": "application/json, text/event-stream"},
        )
        assert response.status_code == 401

    client.portal.call(run)


def test_mcp_helper_conversation_id_scoped_to_its_creator(client: TestClient) -> None:
    token_a = client.post("/api/app-tokens", json={"name": "mcp-helper-a"}).json()["token"]
    token_b = client.post("/api/app-tokens", json={"name": "mcp-helper-b"}).json()["token"]

    async def run() -> None:
        async with _mcp_session(token_a) as (read, write), ClientSession(read, write) as session_a:
            await session_a.initialize()
            conv = _call_tool_json(await session_a.call_tool("create_agent_conversation", {}))
            conversation_id = conv["conversation_id"]

        async with _mcp_session(token_b) as (read, write), ClientSession(read, write) as session_b:
            await session_b.initialize()
            result = _call_tool_json(
                await session_b.call_tool(
                    "create_analysis",
                    {"name": "Not yours", "description": "d", "conversation_id": conversation_id},
                )
            )
            assert result == {"error": "Conversation introuvable", "status_code": 404}

    client.portal.call(run)
