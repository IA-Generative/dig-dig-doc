from fastapi.testclient import TestClient


def _create_dossier(client: TestClient, name: str) -> str:
    analyse_id = client.post(
        "/api/analyses", json={"name": f"Analyse {name}", "description": "Test"}
    ).json()["id"]
    return client.post(
        "/api/dossiers", json={"name": name, "analyse_id": analyse_id}
    ).json()["id"]


def test_list_my_conversations_across_dossiers(client: TestClient) -> None:
    # La suite n'isole pas chaque test dans une transaction annulée (voir
    # les autres tests de pagination, qui s'accumulent aussi) - on vérifie
    # la présence des dossiers de CE test, pas une liste vide.
    dossier_a = _create_dossier(client, "Dossier sidebar A")
    dossier_b = _create_dossier(client, "Dossier sidebar B")

    conversation_a = client.post(f"/api/dossiers/{dossier_a}/conversations").json()
    client.post(f"/api/dossiers/{dossier_b}/conversations")

    listed = client.get("/api/conversations", params={"page_size": 100}).json()["items"]
    listed_ids = {c["dossier_id"] for c in listed}
    assert {dossier_a, dossier_b} <= listed_ids
    # Pas encore de message sur ces deux-là : pas de preview.
    mine = {
        c["dossier_id"]: c for c in listed if c["dossier_id"] in {dossier_a, dossier_b}
    }
    assert mine[dossier_a]["last_message_preview"] is None
    assert mine[dossier_b]["last_message_preview"] is None

    client.post(
        f"/api/dossiers/{dossier_a}/conversations/{conversation_a['id']}/messages",
        json={"content": "Bonjour"},
    )

    listed = client.get("/api/conversations", params={"page_size": 100}).json()["items"]
    # Le dossier avec le message le plus récent (A) passe en tête, comme
    # dans une sidebar de conversations façon ChatGPT.
    assert listed[0]["dossier_id"] == dossier_a
    assert listed[0]["dossier_name"] == "Dossier sidebar A"
    assert listed[0]["last_message_preview"] == "Bonjour"


def test_conversations_list_is_private_to_its_user(client: TestClient) -> None:
    from app.core.security.factory import RequestContext, get_current_user
    from app.main import app

    dossier_id = _create_dossier(client, "Dossier sidebar privé")
    client.post(f"/api/dossiers/{dossier_id}/conversations")

    def as_other_user() -> RequestContext:
        return RequestContext(
            user_id="other-sidebar-user",
            email="other@example.com",
            roles=[],
            is_admin=False,
        )

    app.dependency_overrides[get_current_user] = as_other_user
    try:
        other_listed = client.get("/api/conversations").json()["items"]
        assert all(c["dossier_id"] != dossier_id for c in other_listed)
    finally:
        del app.dependency_overrides[get_current_user]
