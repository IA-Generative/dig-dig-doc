from fastapi.testclient import TestClient


def _create_app_token(client: TestClient, name: str) -> str:
    return client.post("/api/app-tokens", json={"name": name}).json()["token"]


def test_create_and_get_ephemeral_analyse(client: TestClient) -> None:
    created = client.post(
        "/api/ephemeral/analyses",
        json={
            "name": "Analyse éphémère test",
            "description": "Test",
            "classification_prompt": "Classe le document",
            "labels": [{"name": "CNI", "definition": "Carte d'identité"}],
            "extraction_prompt": "Extrait les champs",
            "entities": [{"name": "nom", "definition": "Nom de famille", "type": "texte"}],
            "agents": [{"name": "Cohérence", "prompt": "Vérifie la cohérence"}],
        },
    )
    assert created.status_code == 201
    analyse_id = created.json()["analyse_id"]
    assert analyse_id

    fetched = client.get(f"/api/ephemeral/analyses/{analyse_id}")
    assert fetched.status_code == 200
    body = fetched.json()
    assert body["name"] == "Analyse éphémère test"
    assert body["classification"]["prompt"] == "Classe le document"
    assert [lbl["name"] for lbl in body["classification"]["labels"]] == ["CNI"]
    assert body["extraction"]["prompt"] == "Extrait les champs"
    assert [ent["name"] for ent in body["extraction"]["entities"]] == ["nom"]
    assert [a["name"] for a in body["agents"]] == ["Cohérence"]


def test_get_unknown_ephemeral_analyse_is_404(client: TestClient) -> None:
    response = client.get("/api/ephemeral/analyses/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_classic_analyse_is_not_visible_through_ephemeral_endpoint(client: TestClient) -> None:
    classic = client.post("/api/analyses", json={"name": "Analyse classique", "description": "Test"}).json()
    response = client.get(f"/api/ephemeral/analyses/{classic['id']}")
    assert response.status_code == 404


def test_delete_ephemeral_analyse(client: TestClient) -> None:
    created = client.post("/api/ephemeral/analyses", json={"name": "À supprimer", "description": ""}).json()
    analyse_id = created["analyse_id"]

    response = client.delete(f"/api/ephemeral/analyses/{analyse_id}")
    assert response.status_code == 204

    assert client.get(f"/api/ephemeral/analyses/{analyse_id}").status_code == 404


def test_delete_ephemeral_analyse_referenced_by_a_dossier_is_409(client: TestClient) -> None:
    created = client.post("/api/ephemeral/analyses", json={"name": "Référencée", "description": ""}).json()
    analyse_id = created["analyse_id"]

    client.post("/api/dossiers", json={"name": "Dossier lié", "analyse_id": analyse_id})

    response = client.delete(f"/api/ephemeral/analyses/{analyse_id}")
    assert response.status_code == 409


def test_ephemeral_analyse_is_scoped_to_its_creator(client: TestClient) -> None:
    token_a = _create_app_token(client, "app-a")
    token_b = _create_app_token(client, "app-b")

    created = client.post(
        "/api/ephemeral/analyses",
        json={"name": "Analyse app A", "description": ""},
        headers={"X-App-Token": token_a},
    ).json()
    analyse_id = created["analyse_id"]

    # Visible pour son créateur (le même token API)...
    assert client.get(f"/api/ephemeral/analyses/{analyse_id}", headers={"X-App-Token": token_a}).status_code == 200
    # ... mais pas pour un autre token API, ni pour une session Keycloak (dev-user en test).
    assert client.get(f"/api/ephemeral/analyses/{analyse_id}", headers={"X-App-Token": token_b}).status_code == 404
    assert client.get(f"/api/ephemeral/analyses/{analyse_id}").status_code == 404


def test_invalid_app_token_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/ephemeral/analyses",
        json={"name": "X", "description": ""},
        headers={"X-App-Token": "not-a-real-token"},
    )
    assert response.status_code == 401
