import uuid

from fastapi.testclient import TestClient


def _create_analyse(client: TestClient, name: str = "Analyse dossier test") -> str:
    return client.post("/api/analyses", json={"name": name}).json()["id"]


def test_dossier_requires_an_existing_analyse(client: TestClient) -> None:
    response = client.post("/api/dossiers", json={"name": "Dossier orphelin", "analyse_id": str(uuid.uuid4())})
    assert response.status_code == 400


def test_create_dossier_and_launch_lifecycle(client: TestClient) -> None:
    analyse_id = _create_analyse(client)

    dossier = client.post("/api/dossiers", json={"name": "Dossier 2026-0001", "analyse_id": analyse_id}).json()
    assert dossier["status"] == "en_attente"
    assert dossier["analyse_version"] == "v1"

    dossier = client.post(f"/api/dossiers/{dossier['id']}/launch").json()
    assert dossier["status"] == "en_cours"
    assert dossier["started_at"] is not None
    kinds = {step["kind"] for step in dossier["execution_steps"]}
    assert kinds == {"classification", "extraction"}

    dossier = client.post(f"/api/dossiers/{dossier['id']}/stop").json()
    assert dossier["status"] == "arrêté"
    assert dossier["ended_at"] is not None


def test_launch_adds_one_step_per_agent(client: TestClient) -> None:
    analyse_id = _create_analyse(client, "Analyse avec agent")
    client.post(
        f"/api/analyses/{analyse_id}/agents",
        json={"name": "Cohérence", "prompt": "Vérifie la cohérence.", "tools": [], "output": True},
    )

    dossier = client.post("/api/dossiers", json={"name": "Dossier avec agent", "analyse_id": analyse_id}).json()
    dossier = client.post(f"/api/dossiers/{dossier['id']}/launch").json()

    agent_steps = [step for step in dossier["execution_steps"] if step["kind"] == "agent"]
    assert len(agent_steps) == 1
    assert agent_steps[0]["label"] == "Cohérence"


def test_document_upload_and_label(client: TestClient) -> None:
    analyse_id = _create_analyse(client, "Analyse documents")
    dossier = client.post("/api/dossiers", json={"name": "Dossier documents", "analyse_id": analyse_id}).json()

    dossier = client.post(
        f"/api/dossiers/{dossier['id']}/documents",
        files=[("files", ("cni_recto.jpg", b"fake-bytes", "image/jpeg"))],
    ).json()
    document = dossier["documents"][0]
    assert document["name"] == "cni_recto.jpg"
    assert document["mimetype"] == "image/jpeg"
    assert document["s3_key"].startswith(f"dossiers/{dossier['id']}/")
    assert document["label"] is None

    updated = client.put(
        f"/api/dossiers/{dossier['id']}/documents/{document['id']}/label", json={"label": "CNI"}
    ).json()
    assert updated["label"] == "CNI"


def test_conversation_and_message_lifecycle(client: TestClient) -> None:
    analyse_id = _create_analyse(client, "Analyse conversation")
    dossier = client.post("/api/dossiers", json={"name": "Dossier chat", "analyse_id": analyse_id}).json()
    dossier_id = dossier["id"]

    conversation = client.post(f"/api/dossiers/{dossier_id}/conversations").json()
    assert conversation["dossier_id"] == dossier_id
    assert conversation["user_id"] == "dev-user"
    assert conversation["messages"] == []

    conversation = client.post(
        f"/api/dossiers/{dossier_id}/conversations/{conversation['id']}/messages",
        json={"content": "Quel est le statut du dossier ?"},
    ).json()
    assert len(conversation["messages"]) == 1
    assert conversation["messages"][0]["role"] == "user"
    assert conversation["messages"][0]["content"] == "Quel est le statut du dossier ?"

    listed = client.get(f"/api/dossiers/{dossier_id}/conversations").json()
    assert len(listed) == 1
    assert listed[0]["id"] == conversation["id"]


INTERNAL_HEADERS = {"X-Worker-Token": "dev-only-worker-token-not-for-prod"}


def test_internal_routes_require_worker_token(client: TestClient) -> None:
    response = client.post(f"/api/internal/execution-steps/{uuid.uuid4()}/logs", json={"message": "hello"})
    assert response.status_code in (401, 422)  # 422 si le header est simplement absent


def test_execution_step_logs_and_completion(client: TestClient) -> None:
    analyse_id = _create_analyse(client, "Analyse logs")
    dossier = client.post("/api/dossiers", json={"name": "Dossier logs", "analyse_id": analyse_id}).json()
    dossier = client.post(f"/api/dossiers/{dossier['id']}/launch").json()
    step_id = dossier["execution_steps"][0]["id"]

    step = client.post(
        f"/api/internal/execution-steps/{step_id}/logs",
        json={"level": "info", "message": "Lecture du document..."},
        headers=INTERNAL_HEADERS,
    ).json()
    assert len(step["logs"]) == 1
    assert step["logs"][0]["message"] == "Lecture du document..."

    step = client.post(
        f"/api/internal/execution-steps/{step_id}/complete",
        json={"status": "terminé", "output": "CNI (confiance : 96%)"},
        headers=INTERNAL_HEADERS,
    ).json()
    assert step["status"] == "terminé"
    assert step["output"] == "CNI (confiance : 96%)"
    assert step["ended_at"] is not None


def test_document_pages_predictions_and_validation(client: TestClient) -> None:
    analyse_id = _create_analyse(client, "Analyse pages")
    dossier = client.post("/api/dossiers", json={"name": "Dossier pages", "analyse_id": analyse_id}).json()
    dossier = client.post(
        f"/api/dossiers/{dossier['id']}/documents",
        files=[("files", ("cni.pdf", b"fake-bytes", "application/pdf"))],
    ).json()
    document_id = dossier["documents"][0]["id"]

    page = client.post(
        f"/api/internal/documents/{document_id}/pages",
        json={"page_number": 1, "width": 1000, "height": 1400, "content": "REPUBLIQUE FRANCAISE ..."},
        headers=INTERNAL_HEADERS,
    ).json()
    assert page["page_number"] == 1
    assert page["content"].startswith("REPUBLIQUE")
    assert page["predictions"] == []

    prediction = client.post(
        f"/api/internal/pages/{page['id']}/predictions",
        json={
            "kind": "label",
            "name": "CNI",
            "value": "CNI",
            "confidence": 0.96,
            "bbox": {"x_min": 0.1, "y_min": 0.1, "x_max": 0.9, "y_max": 0.5},
        },
        headers=INTERNAL_HEADERS,
    ).json()
    assert prediction["kind"] == "label"
    assert prediction["bbox"]["x_max"] == 0.9
    assert prediction["validations"] == []

    dossier = client.get(f"/api/dossiers/{dossier['id']}").json()
    fetched_page = dossier["documents"][0]["pages"][0]
    assert fetched_page["predictions"][0]["name"] == "CNI"

    validated = client.put(
        f"/api/dossiers/{dossier['id']}/documents/{document_id}/pages/{page['id']}"
        f"/predictions/{prediction['id']}/validations",
        json={"status": "corrigé", "corrected_value": "Carte Nationale d'Identité"},
    ).json()
    assert validated["status"] == "corrigé"
    assert validated["corrected_value"] == "Carte Nationale d'Identité"
    assert validated["validator_user_id"] == "dev-user"


def test_assistant_message_with_sources(client: TestClient) -> None:
    analyse_id = _create_analyse(client, "Analyse sources")
    dossier = client.post("/api/dossiers", json={"name": "Dossier sources", "analyse_id": analyse_id}).json()
    dossier_id = dossier["id"]
    dossier = client.post(
        f"/api/dossiers/{dossier_id}/documents",
        files=[("files", ("cni.pdf", b"fake-bytes", "application/pdf"))],
    ).json()
    document_id = dossier["documents"][0]["id"]
    conversation = client.post(f"/api/dossiers/{dossier_id}/conversations").json()

    conversation = client.post(
        f"/api/internal/conversations/{conversation['id']}/messages",
        json={
            "content": "Le document est une CNI.",
            "sources": [{"dossier_document_id": document_id, "excerpt": "REPUBLIQUE FRANCAISE"}],
        },
        headers=INTERNAL_HEADERS,
    ).json()
    assert len(conversation["messages"]) == 1
    message = conversation["messages"][0]
    assert message["role"] == "assistant"
    assert len(message["sources"]) == 1
    assert message["sources"][0]["dossier_document_id"] == document_id


def test_execution_stream_sends_terminal_state(client: TestClient) -> None:
    analyse_id = _create_analyse(client, "Analyse SSE")
    dossier = client.post("/api/dossiers", json={"name": "Dossier SSE", "analyse_id": analyse_id}).json()
    dossier = client.post(f"/api/dossiers/{dossier['id']}/launch").json()
    for step in dossier["execution_steps"]:
        client.post(
            f"/api/internal/execution-steps/{step['id']}/complete",
            json={"status": "terminé", "output": "ok"},
            headers=INTERNAL_HEADERS,
        )
    # Un dossier n'a pas de transition automatique "toutes les étapes sont
    # terminées -> dossier terminé" pour l'instant (ça viendra avec le
    # worker) : on l'arrête explicitement pour obtenir un statut terminal et
    # que le flux SSE se termine.
    dossier = client.post(f"/api/dossiers/{dossier['id']}/stop").json()
    assert dossier["status"] == "arrêté"

    with client.stream("GET", f"/api/dossiers/{dossier['id']}/stream") as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())
    assert "execution-update" in body
    assert "arr" in body  # "arrêté", échappé ou non selon l'encodage JSON
