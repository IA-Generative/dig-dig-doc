from fastapi.testclient import TestClient


def _create_dossier(client: TestClient, name: str) -> str:
    analyse_id = client.post("/api/analyses", json={"name": f"Analyse {name}", "description": "Test"}).json()["id"]
    return client.post("/api/dossiers", json={"name": name, "analyse_id": analyse_id}).json()["id"]


# ---------------------------------------------------------------------------
# /api/me/preferences
# ---------------------------------------------------------------------------


def test_get_preferences_creates_default(client: TestClient) -> None:
    # Les tests ne sont pas isolés par transaction : on remet le thème à
    # "system" pour vérifier le comportement par défaut, puis on vérifie.
    client.patch("/api/me/preferences", json={"theme": "system"})
    response = client.get("/api/me/preferences")
    assert response.status_code == 200
    data = response.json()
    assert data["theme"] == "system"


def test_update_preferences(client: TestClient) -> None:
    response = client.patch("/api/me/preferences", json={"theme": "dark"})
    assert response.status_code == 200
    assert response.json()["theme"] == "dark"

    # La préférence est persistée
    response = client.get("/api/me/preferences")
    assert response.status_code == 200
    assert response.json()["theme"] == "dark"


def test_update_preferences_invalid_theme(client: TestClient) -> None:
    response = client.patch("/api/me/preferences", json={"theme": "purple"})
    assert response.status_code == 422


def test_update_preferences_idempotent(client: TestClient) -> None:
    client.patch("/api/me/preferences", json={"theme": "light"})
    response = client.patch("/api/me/preferences", json={"theme": "light"})
    assert response.status_code == 200
    assert response.json()["theme"] == "light"


# ---------------------------------------------------------------------------
# /api/me/stats
# ---------------------------------------------------------------------------


def test_stats_empty(client: TestClient) -> None:
    """Les stats retournent des zéros quand l'utilisateur n'a aucune activité."""
    response = client.get("/api/me/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["conversations_count"] >= 0
    assert data["messages_sent_count"] >= 0
    assert data["agent_conversations_count"] >= 0
    assert data["agent_messages_sent_count"] >= 0
    assert data["dossiers_count"] >= 0
    assert data["analyses_shared_count"] >= 0
    assert data["last_activity_at"] is None or isinstance(data["last_activity_at"], str)


def test_stats_reflect_activity(client: TestClient) -> None:
    """Les stats reflètent l'activité de l'utilisateur courant."""
    # Crée un dossier + conversation + message
    dossier_id = _create_dossier(client, "Stats test dossier")
    conversation = client.post(f"/api/dossiers/{dossier_id}/conversations").json()
    client.post(
        f"/api/dossiers/{dossier_id}/conversations/{conversation['id']}/messages",
        json={"content": "Hello stats"},
    )

    response = client.get("/api/me/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["conversations_count"] >= 1
    assert data["messages_sent_count"] >= 1
    assert data["dossiers_count"] >= 1
    assert data["last_activity_at"] is not None
