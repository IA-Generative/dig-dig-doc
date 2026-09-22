from fastapi.testclient import TestClient


def test_create_and_get_analyse(client: TestClient) -> None:
    response = client.post("/api/analyses", json={"name": "Contrôle CNI", "description": "Lot de test"})
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Contrôle CNI"
    assert body["classification"]["labels"] == []
    assert body["agents"] == []

    response = client.get(f"/api/analyses/{body['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == body["id"]


def test_classification_prompt_is_versioned(client: TestClient) -> None:
    analyse = client.post("/api/analyses", json={"name": "Avis d'imposition"}).json()
    analyse_id = analyse["id"]

    client.put(f"/api/analyses/{analyse_id}/classification/prompt", json={"prompt": "Identifie le document."})
    response = client.put(
        f"/api/analyses/{analyse_id}/classification/prompt", json={"prompt": "Identifie le document (v2)."}
    )

    body = response.json()
    assert body["classification"]["prompt"] == "Identifie le document (v2)."
    versions = body["classification"]["prompt_versions"]
    assert len(versions) == 2
    assert versions[0]["content"] == "Identifie le document."

    version_id = versions[0]["id"]
    restored = client.post(f"/api/analyses/{analyse_id}/classification/prompt/restore/{version_id}").json()
    assert restored["classification"]["prompt"] == "Identifie le document."


def test_labels_round_trip_and_version(client: TestClient) -> None:
    analyse = client.post("/api/analyses", json={"name": "Labels test"}).json()
    analyse_id = analyse["id"]

    body = client.put(
        f"/api/analyses/{analyse_id}/classification/labels",
        json={"labels": [{"name": "CNI", "definition": "Carte nationale d'identité."}]},
    ).json()
    assert [label["name"] for label in body["classification"]["labels"]] == ["CNI"]
    # Versioned from the very first change too: the snapshot is the prior
    # (empty) state.
    assert len(body["classification"]["labels_versions"]) == 1
    assert body["classification"]["labels_versions"][0]["content"] == []

    body = client.put(f"/api/analyses/{analyse_id}/classification/labels", json={"labels": []}).json()
    assert body["classification"]["labels"] == []
    assert len(body["classification"]["labels_versions"]) == 2


def test_share_by_email_returns_working_link(client: TestClient) -> None:
    analyse = client.post("/api/analyses", json={"name": "Analyse partagée"}).json()

    share = client.post(
        f"/api/analyses/{analyse['id']}/shares",
        json={"kind": "email", "email": "instructeur.externe@example.com"},
    ).json()
    assert share["kind"] == "email"
    assert share["email"] == "instructeur.externe@example.com"
    assert share["share_url"] is not None
    token = share["share_url"].rsplit("/", 1)[-1]

    # Le jeton en clair n'est jamais renvoyé une seconde fois.
    listed = client.get(f"/api/analyses/{analyse['id']}/shares").json()
    assert listed[0]["share_url"] is None

    shared = client.get(f"/api/analyses/shared/{token}").json()
    assert shared["id"] == analyse["id"]

    # Un jeton invalide ne donne accès à rien.
    assert client.get("/api/analyses/shared/not-a-real-token").status_code == 404

    client.delete(f"/api/analyses/{analyse['id']}/shares/{share['id']}")
    assert client.get(f"/api/analyses/shared/{token}").status_code == 404


def test_share_by_keycloak_group(client: TestClient) -> None:
    analyse = client.post("/api/analyses", json={"name": "Analyse partagée par groupe"}).json()

    share = client.post(
        f"/api/analyses/{analyse['id']}/shares", json={"kind": "keycloak_group", "keycloak_group": "prefecture-75"}
    ).json()
    assert share["kind"] == "keycloak_group"
    assert share["keycloak_group"] == "prefecture-75"
    assert share["share_url"] is None


def test_agent_lifecycle_and_output_versioning(client: TestClient) -> None:
    analyse = client.post("/api/analyses", json={"name": "Agents test"}).json()
    analyse_id = analyse["id"]

    agent = client.post(
        f"/api/analyses/{analyse_id}/agents",
        json={"name": "Synthèse", "prompt": "Rédige une synthèse.", "tools": ["lecture_document"], "output": True},
    ).json()
    assert agent["output"] is True
    assert agent["tools"] == ["lecture_document"]

    agent = client.put(f"/api/analyses/{analyse_id}/agents/{agent['id']}/output", json={"output": False}).json()
    assert agent["output"] is False
    assert len(agent["output_versions"]) == 1
    assert agent["output_versions"][0]["content"] is True
