"""Affectation des dossiers (issue #173) : annuaire local, affectation unitaire et en lot, journal, filtre."""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.security.factory import RequestContext, get_current_user
from app.main import app


def _person(user_id: str, first: str, last: str) -> RequestContext:
    return RequestContext(
        user_id=user_id, email=f"{user_id}@example.org", roles=[], is_admin=False, first_name=first, last_name=last
    )


@pytest.fixture
def people(client: TestClient):
    """Deux personnes connues de l'annuaire (elles se « connectent » via /api/auth/me)."""
    suffix = uuid.uuid4().hex[:8]
    known = {
        "camille": _person(f"camille-{suffix}", "Camille", f"Durand{suffix}"),
        "samir": _person(f"samir-{suffix}", "Samir", f"Benali{suffix}"),
    }
    for person in known.values():
        app.dependency_overrides[get_current_user] = lambda person=person: person
        try:
            assert client.get("/api/auth/me").status_code == 200
        finally:
            del app.dependency_overrides[get_current_user]
    return known


def _dossier(client: TestClient, name: str = "Dossier affectation") -> dict:
    analyse = client.post("/api/analyses", json={"name": "Affectation", "description": "Test"}).json()
    return client.post("/api/dossiers", json={"name": name, "analyse_id": analyse["id"]}).json()


def _assign(client: TestClient, dossier_id: str, assignee_id: str | None):
    return client.put(f"/api/dossiers/{dossier_id}/assignee", json={"assignee_id": assignee_id})


def _events(client: TestClient, dossier_id: str) -> list[dict]:
    return client.get(f"/api/dossiers/{dossier_id}/events", params={"type": "assignee_changed"}).json()["items"]


# --- Annuaire ---


def test_login_registers_the_person_in_the_directory(client: TestClient, people) -> None:
    camille = people["camille"]

    found = client.get("/api/users", params={"q": camille.last_name}).json()

    assert found == [{"id": camille.user_id, "name": f"Camille {camille.last_name}"}]


def test_directory_search_ignores_case_and_wildcards(client: TestClient, people) -> None:
    camille = people["camille"]

    assert [p["id"] for p in client.get("/api/users", params={"q": camille.last_name.upper()}).json()] == [
        camille.user_id
    ]
    # « % » et « _ » sont des caractères ordinaires, pas des jokers.
    assert client.get("/api/users", params={"q": "%"}).json() == []


def test_directory_does_not_expose_emails(client: TestClient, people) -> None:
    assert all(set(p) == {"id", "name"} for p in client.get("/api/users").json())


# --- Affectation unitaire ---


def test_new_dossier_is_unassigned(client: TestClient) -> None:
    dossier = _dossier(client)

    assert dossier["assignee"] is None and dossier["assigned_at"] is None


def test_assign_reassign_and_unassign(client: TestClient, people) -> None:
    dossier = _dossier(client)
    camille, samir = people["camille"], people["samir"]

    first = _assign(client, dossier["id"], camille.user_id).json()
    assert first["assignee"] == {"id": camille.user_id, "name": f"Camille {camille.last_name}"}
    assert first["assigned_at"] is not None

    second = _assign(client, dossier["id"], samir.user_id).json()
    assert second["assignee"]["id"] == samir.user_id

    third = _assign(client, dossier["id"], None).json()
    assert third["assignee"] is None and third["assigned_at"] is None


def test_unknown_person_cannot_receive_a_dossier(client: TestClient) -> None:
    dossier = _dossier(client)

    response = _assign(client, dossier["id"], "personne-inconnue")

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "unknown_user"
    assert client.get(f"/api/dossiers/{dossier['id']}").json()["assignee"] is None


def test_assign_unknown_dossier_is_404(client: TestClient, people) -> None:
    assert _assign(client, str(uuid.uuid4()), people["camille"].user_id).status_code == 404


def test_assignment_is_traced_in_the_journal(client: TestClient, people) -> None:
    dossier = _dossier(client)
    camille, samir = people["camille"], people["samir"]

    _assign(client, dossier["id"], camille.user_id)
    _assign(client, dossier["id"], samir.user_id)
    _assign(client, dossier["id"], None)

    payloads = [e["payload"] for e in reversed(_events(client, dossier["id"]))]
    assert payloads[0] == {"from": None, "to": {"id": camille.user_id, "name": f"Camille {camille.last_name}"}}
    assert payloads[1]["from"]["id"] == camille.user_id and payloads[1]["to"]["id"] == samir.user_id
    assert payloads[2]["from"]["id"] == samir.user_id and payloads[2]["to"] is None
    assert _events(client, dossier["id"])[0]["actor_id"] == "dev-user"


def test_assigning_to_the_same_person_writes_nothing(client: TestClient, people) -> None:
    dossier = _dossier(client)
    _assign(client, dossier["id"], people["camille"].user_id)

    _assign(client, dossier["id"], people["camille"].user_id)
    _assign(client, _dossier(client)["id"], None)

    assert len(_events(client, dossier["id"])) == 1


# --- Affectation en lot ---


def _bulk(client: TestClient, ids: list[str], assignee_id: str | None):
    return client.put("/api/dossiers/bulk-assignee", json={"dossier_ids": ids, "assignee_id": assignee_id})


def test_bulk_assignment_updates_every_dossier(client: TestClient, people) -> None:
    dossiers = [_dossier(client, f"Lot {i}") for i in range(3)]
    ids = [d["id"] for d in dossiers]
    camille = people["camille"]

    result = _bulk(client, ids, camille.user_id)

    assert result.status_code == 200 and result.json() == {"updated": 3, "unchanged": 0}
    for dossier_id in ids:
        assert client.get(f"/api/dossiers/{dossier_id}").json()["assignee"]["id"] == camille.user_id
        assert len(_events(client, dossier_id)) == 1


def test_bulk_assignment_counts_unchanged_and_deduplicates(client: TestClient, people) -> None:
    first, second = _dossier(client, "Lot A"), _dossier(client, "Lot B")
    _assign(client, first["id"], people["camille"].user_id)

    result = _bulk(client, [first["id"], second["id"], second["id"]], people["camille"].user_id).json()

    assert result == {"updated": 1, "unchanged": 1}


def test_bulk_unassign(client: TestClient, people) -> None:
    dossier = _dossier(client)
    _assign(client, dossier["id"], people["camille"].user_id)

    assert _bulk(client, [dossier["id"]], None).json() == {"updated": 1, "unchanged": 0}
    assert client.get(f"/api/dossiers/{dossier['id']}").json()["assignee"] is None


def test_bulk_assignment_is_all_or_nothing(client: TestClient, people) -> None:
    dossier = _dossier(client)
    ghost = str(uuid.uuid4())

    response = _bulk(client, [dossier["id"], ghost], people["camille"].user_id)

    assert response.status_code == 404
    assert response.json()["detail"]["dossier_ids"] == [ghost]
    assert client.get(f"/api/dossiers/{dossier['id']}").json()["assignee"] is None
    assert _events(client, dossier["id"]) == []


def test_bulk_assignment_limits(client: TestClient, people) -> None:
    assert _bulk(client, [], people["camille"].user_id).status_code == 422
    assert _bulk(client, [str(uuid.uuid4()) for _ in range(201)], people["camille"].user_id).status_code == 422
    assert _bulk(client, [_dossier(client)["id"]], "personne-inconnue").status_code == 422


# --- Filtre de la liste ---


def _listed_ids(client: TestClient, **params) -> set[str]:
    ids: set[str] = set()
    page = 1
    while True:
        body = client.get("/api/dossiers", params={"page": page, "page_size": 100, **params}).json()
        ids |= {d["id"] for d in body["items"]}
        if page >= body["pages"]:
            return ids
        page += 1


def test_list_filters_by_assignee(client: TestClient, people) -> None:
    camille, samir = people["camille"], people["samir"]
    mine, theirs, nobody = _dossier(client, "Filtre 1"), _dossier(client, "Filtre 2"), _dossier(client, "Filtre 3")
    _assign(client, mine["id"], camille.user_id)
    _assign(client, theirs["id"], samir.user_id)

    assert _listed_ids(client, assignee=camille.user_id) == {mine["id"]}
    assert nobody["id"] in _listed_ids(client, assignee="none")
    assert not {mine["id"], theirs["id"]} & _listed_ids(client, assignee="none")


def test_list_assignee_me_means_the_current_user(client: TestClient, people) -> None:
    dossier = _dossier(client)
    app.dependency_overrides[get_current_user] = lambda: people["camille"]
    try:
        client.put(f"/api/dossiers/{dossier['id']}/assignee", json={"assignee_id": people["camille"].user_id})
        assert dossier["id"] in _listed_ids(client, assignee="me")
    finally:
        del app.dependency_overrides[get_current_user]
    assert dossier["id"] not in _listed_ids(client, assignee="me")  # « moi » = dev-user ici
