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
