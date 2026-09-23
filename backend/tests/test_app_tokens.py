from fastapi.testclient import TestClient


def test_create_list_and_use_app_token(client: TestClient) -> None:
    created = client.post("/api/app-tokens", json={"name": "worker-document-process"}).json()
    assert created["name"] == "worker-document-process"
    assert created["created_by"] == "dev-user"
    assert created["revoked_at"] is None
    assert created["last_used_at"] is None
    token = created["token"]
    assert token

    listed = client.get("/api/app-tokens").json()["items"]
    assert any(t["id"] == created["id"] for t in listed)
    # Le jeton en clair n'est jamais renvoyé une seconde fois.
    assert all("token" not in t for t in listed)

    # Le jeton créé fonctionne comme un vrai jeton d'app sur les routes
    # internes, au même titre qu'INTERNAL_WORKER_TOKEN.
    response = client.post(
        "/api/internal/execution-steps/00000000-0000-0000-0000-000000000000/logs",
        json={"message": "hello"},
        headers={"X-App-Token": token},
    )
    assert response.status_code == 404  # jeton accepté, l'étape n'existe juste pas

    response = client.post(
        "/api/internal/execution-steps/00000000-0000-0000-0000-000000000000/logs",
        json={"message": "hello"},
        headers={"X-App-Token": "not-a-real-token"},
    )
    assert response.status_code == 401


def test_revoked_app_token_is_rejected(client: TestClient) -> None:
    created = client.post("/api/app-tokens", json={"name": "temp-script"}).json()
    token = created["token"]

    client.delete(f"/api/app-tokens/{created['id']}")

    response = client.post(
        "/api/internal/execution-steps/00000000-0000-0000-0000-000000000000/logs",
        json={"message": "hello"},
        headers={"X-App-Token": token},
    )
    assert response.status_code == 401
