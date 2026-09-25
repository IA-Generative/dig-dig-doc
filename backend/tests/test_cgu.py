"""Tests des CGU versionnées et de l'acceptation par les utilisateurs.

Les tests ne peuvent pas assumer un état vide de la DB (les versions
créées par les tests précédents persistent). Chaque test crée donc ses
propres versions et vérifie les comportements relatifs.
"""
from fastapi.testclient import TestClient


def _create_version(client: TestClient, content: str = "# CGU") -> dict:
    """Crée une version CGU et retourne le JSON."""
    response = client.post("/api/admin/cgu", json={"content": content})
    assert response.status_code == 201
    return response.json()


def _activate(client: TestClient, cgu_id: str) -> dict:
    response = client.post(f"/api/admin/cgu/{cgu_id}/activate")
    assert response.status_code == 200
    return response.json()


def test_get_active_cgu(client: TestClient) -> None:
    """GET /api/cgu retourne la version active."""
    version = _create_version(client, "# CGU test_get_active")
    _activate(client, version["id"])

    response = client.get("/api/cgu")
    assert response.status_code == 200
    data = response.json()
    assert data["content"] == "# CGU test_get_active"


def test_acceptance_status_with_active_cgu(client: TestClient) -> None:
    """L'utilisateur n'a pas accepté par défaut après activation d'une CGU."""
    version = _create_version(client, "# CGU test_acceptance")
    _activate(client, version["id"])

    status = client.get("/api/cgu/acceptance")
    assert status.status_code == 200
    data = status.json()
    assert data["cgu"] is not None
    assert data["cgu"]["id"] == version["id"]


def test_accept_cgu(client: TestClient) -> None:
    """L'utilisateur peut accepter la version active."""
    version = _create_version(client, "# CGU test_accept")
    _activate(client, version["id"])

    accepted = client.post("/api/cgu/acceptance")
    assert accepted.status_code == 200
    assert accepted.json()["accepted"] is True

    status = client.get("/api/cgu/acceptance")
    assert status.json()["accepted"] is True

    # Idempotent
    assert client.post("/api/cgu/acceptance").status_code == 200


def test_list_versions(client: TestClient) -> None:
    _create_version(client, "# v-list-1")
    _create_version(client, "# v-list-2")

    listed = client.get("/api/admin/cgu/versions")
    assert listed.status_code == 200
    versions = listed.json()
    assert len(versions) >= 2
    # Triées par version décroissante
    assert versions[0]["version"] >= versions[1]["version"]


def test_update_non_active_version(client: TestClient) -> None:
    version = _create_version(client, "# Original")

    updated = client.patch(f"/api/admin/cgu/{version['id']}", json={"content": "# Modifié"})
    assert updated.status_code == 200
    assert updated.json()["content"] == "# Modifié"


def test_update_active_version_returns_400(client: TestClient) -> None:
    version = _create_version(client, "# Active")
    _activate(client, version["id"])

    response = client.patch(f"/api/admin/cgu/{version['id']}", json={"content": "# Tentative"})
    assert response.status_code == 400


def test_new_version_requires_re_acceptance(client: TestClient) -> None:
    # Crée et active v1, l'utilisateur accepte
    v1 = _create_version(client, "# v1 re-acceptance")
    _activate(client, v1["id"])
    client.post("/api/cgu/acceptance")

    assert client.get("/api/cgu/acceptance").json()["accepted"] is True

    # Crée et active v2 : l'utilisateur doit réaccepter
    v2 = _create_version(client, "# v2 re-acceptance")
    assert v2["version"] > v1["version"]
    _activate(client, v2["id"])

    status = client.get("/api/cgu/acceptance").json()
    assert status["accepted"] is False
    assert status["cgu"]["version"] == v2["version"]

    # L'utilisateur accepte la nouvelle version
    client.post("/api/cgu/acceptance")
    assert client.get("/api/cgu/acceptance").json()["accepted"] is True


def test_acceptance_routes_require_auth(client: TestClient, monkeypatch) -> None:
    """Les routes /acceptance nécessitent une authentification."""
    from fastapi import HTTPException, status

    class NoAuth:
        def __call__(self, request):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    monkeypatch.setattr("app.core.security.factory.TokenVerifier", NoAuth())

    response = client.get("/api/cgu/acceptance")
    assert response.status_code == 401
