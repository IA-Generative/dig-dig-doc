"""Tests pour les résumés de documents/dossiers et le hash de fichier (issue #52).

Couvre :
- Les endpoints internes de dépôt de résumé et de hash (worker → backend).
- Les endpoints publics de régénération de résumé (backend → Celery).
- Le versioning append-only : un nouveau résumé devient le "latest".
- La présence des champs summary_status / file_hash dans les réponses API.
"""

import uuid

from fastapi.testclient import TestClient

_INTERNAL_HEADERS = {"X-App-Token": "dev-only-worker-token-not-for-prod"}


def _create_analyse(client: TestClient, name: str = "Analyse résumés") -> str:
    return client.post("/api/analyses", json={"name": name, "description": "Test"}).json()["id"]


def _create_dossier_with_document(client: TestClient) -> tuple[str, str]:
    """Crée un dossier avec un document et retourne (dossier_id, document_id)."""
    analyse_id = _create_analyse(client)
    dossier = client.post("/api/dossiers", json={"name": "Dossier résumé", "analyse_id": analyse_id}).json()
    dossier = client.post(
        f"/api/dossiers/{dossier['id']}/documents",
        files=[("files", ("cni.pdf", b"fake-bytes", "application/pdf"))],
    ).json()
    return dossier["id"], dossier["documents"][0]["id"]


# ---------------------------------------------------------------------------
# Champs summary_status / file_hash dans les réponses
# ---------------------------------------------------------------------------


def test_dossier_document_has_summary_fields(client: TestClient) -> None:
    _, document_id = _create_dossier_with_document(client)

    response = client.get(f"/api/internal/documents/{document_id}", headers=_INTERNAL_HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert body["summary_status"] == "en_attente"
    assert body["summary_error"] is None
    assert body["summary"] is None
    assert body["file_hash"] is None


def test_dossier_has_summary_fields(client: TestClient) -> None:
    analyse_id = _create_analyse(client)
    dossier = client.post(
        "/api/dossiers", json={"name": "Dossier champs résumé", "analyse_id": analyse_id}
    ).json()

    response = client.get(f"/api/dossiers/{dossier['id']}")
    assert response.status_code == 200
    body = response.json()
    assert body["summary_status"] == "en_attente"
    assert body["summary_error"] is None
    assert body["summary"] is None


# ---------------------------------------------------------------------------
# Hash de fichier (worker → backend)
# ---------------------------------------------------------------------------


def test_internal_set_file_hash(client: TestClient) -> None:
    _, document_id = _create_dossier_with_document(client)

    response = client.put(
        f"/api/internal/documents/{document_id}/file-hash",
        json={"file_hash": "abc123def456"},
        headers=_INTERNAL_HEADERS,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["file_hash"] == "abc123def456"

    # Vérifie la persistance via GET
    doc = client.get(f"/api/internal/documents/{document_id}", headers=_INTERNAL_HEADERS).json()
    assert doc["file_hash"] == "abc123def456"


def test_internal_set_file_hash_404(client: TestClient) -> None:
    response = client.put(
        f"/api/internal/documents/{uuid.uuid4()}/file-hash",
        json={"file_hash": "abc"},
        headers=_INTERNAL_HEADERS,
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Statut de résumé (worker → backend)
# ---------------------------------------------------------------------------


def test_internal_set_document_summary_status(client: TestClient) -> None:
    _, document_id = _create_dossier_with_document(client)

    response = client.put(
        f"/api/internal/documents/{document_id}/summary-status",
        json={"status": "en_cours"},
        headers=_INTERNAL_HEADERS,
    )
    assert response.status_code == 200
    assert response.json()["summary_status"] == "en_cours"

    response = client.put(
        f"/api/internal/documents/{document_id}/summary-status",
        json={"status": "échec", "error": "LLM indisponible"},
        headers=_INTERNAL_HEADERS,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["summary_status"] == "échec"
    assert body["summary_error"] == "LLM indisponible"


def test_internal_set_dossier_summary_status(client: TestClient) -> None:
    analyse_id = _create_analyse(client)
    dossier = client.post(
        "/api/dossiers", json={"name": "Dossier statut résumé", "analyse_id": analyse_id}
    ).json()

    response = client.put(
        f"/api/internal/dossiers/{dossier['id']}/summary-status",
        json={"status": "en_cours"},
        headers=_INTERNAL_HEADERS,
    )
    assert response.status_code == 200
    assert response.json()["summary_status"] == "en_cours"


# ---------------------------------------------------------------------------
# Dépôt de résumé (versioning append-only)
# ---------------------------------------------------------------------------


def test_internal_deposit_document_summary(client: TestClient) -> None:
    _, document_id = _create_dossier_with_document(client)

    response = client.post(
        f"/api/internal/documents/{document_id}/summaries",
        json={"content": "Premier résumé du document.", "model": "gpt-4o"},
        headers=_INTERNAL_HEADERS,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["content"] == "Premier résumé du document."
    assert body["model"] == "gpt-4o"
    assert body["id"] is not None

    first_summary_id = body["id"]

    # Un second dépôt crée une nouvelle version (append-only) : le "latest"
    # change mais l'ancien existe toujours en base.
    response = client.post(
        f"/api/internal/documents/{document_id}/summaries",
        json={"content": "Second résumé, plus récent.", "model": "gpt-4o-mini"},
        headers=_INTERNAL_HEADERS,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["content"] == "Second résumé, plus récent."
    assert body["id"] != first_summary_id

    # Vérifie que le document parent a bien summary_status=terminé et que
    # le dernier résumé est le bon (via GET /internal/documents/{id}).
    doc = client.get(f"/api/internal/documents/{document_id}", headers=_INTERNAL_HEADERS).json()
    assert doc["summary_status"] == "terminé"
    assert doc["summary"]["content"] == "Second résumé, plus récent."


def test_internal_deposit_dossier_summary(client: TestClient) -> None:
    analyse_id = _create_analyse(client)
    dossier = client.post(
        "/api/dossiers", json={"name": "Dossier dépôt résumé", "analyse_id": analyse_id}
    ).json()

    response = client.post(
        f"/api/internal/dossiers/{dossier['id']}/summaries",
        json={"content": "Résumé global du dossier.", "model": "gpt-4o"},
        headers=_INTERNAL_HEADERS,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["content"] == "Résumé global du dossier."
    assert body["model"] == "gpt-4o"

    # Vérifie que le dossier parent a bien summary_status=terminé.
    d = client.get(f"/api/dossiers/{dossier['id']}").json()
    assert d["summary_status"] == "terminé"
    assert d["summary"]["content"] == "Résumé global du dossier."


def test_internal_deposit_summary_404(client: TestClient) -> None:
    response = client.post(
        f"/api/internal/documents/{uuid.uuid4()}/summaries",
        json={"content": "x", "model": None},
        headers=_INTERNAL_HEADERS,
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Régénération de résumé (backend → Celery)
# ---------------------------------------------------------------------------


def test_regenerate_document_summary_dispatches_task(client: TestClient, monkeypatch) -> None:
    dossier_id, document_id = _create_dossier_with_document(client)

    dispatched: list[tuple] = []
    monkeypatch.setattr("app.routers.dossiers.dispatch_document_summary", lambda d, doc: dispatched.append((d, doc)))

    response = client.post(f"/api/dossiers/{dossier_id}/documents/{document_id}/summary")
    assert response.status_code == 200
    assert dispatched == [(dossier_id, document_id)]


def test_regenerate_dossier_summary_dispatches_task(client: TestClient, monkeypatch) -> None:
    analyse_id = _create_analyse(client)
    dossier = client.post(
        "/api/dossiers", json={"name": "Dossier régénère résumé", "analyse_id": analyse_id}
    ).json()

    dispatched: list[str] = []
    monkeypatch.setattr("app.routers.dossiers.dispatch_dossier_summary", lambda d: dispatched.append(d))

    response = client.post(f"/api/dossiers/{dossier['id']}/summary")
    assert response.status_code == 200
    assert dispatched == [dossier["id"]]


def test_regenerate_document_summary_404(client: TestClient) -> None:
    analyse_id = _create_analyse(client)
    dossier = client.post(
        "/api/dossiers", json={"name": "Dossier 404 résumé", "analyse_id": analyse_id}
    ).json()

    response = client.post(f"/api/dossiers/{dossier['id']}/documents/{uuid.uuid4()}/summary")
    assert response.status_code == 404
