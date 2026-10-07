"""Tableau de suivi (issue #173) : liste serveur filtrée, recherchée, triée et paginée."""

import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.security.factory import RequestContext, get_current_user
from app.main import app
from app.services.due_date import today_in_paris


def _day(offset: int) -> str:
    return (today_in_paris() + timedelta(days=offset)).isoformat()


@pytest.fixture
def analyse(client: TestClient) -> dict:
    """Une analyse neuve : la base de test contient d'autres dossiers, on se limite à celle-ci avec `analyse_id`."""
    created = client.post("/api/analyses", json={"name": f"Suivi {uuid.uuid4().hex[:6]}", "description": "Test"}).json()
    return client.get(f"/api/analyses/{created['id']}").json()


def _dossier(client: TestClient, analyse: dict, name: str) -> dict:
    return client.post("/api/dossiers", json={"name": name, "analyse_id": analyse["id"]}).json()


def _track(client: TestClient, analyse: dict, **params) -> dict:
    return client.get("/api/tracking", params={"analyse_id": analyse["id"], "page_size": 100, **params}).json()


def _names(client: TestClient, analyse: dict, **params) -> list[str]:
    return [row["name"] for row in _track(client, analyse, **params)["items"]]


def _person(client: TestClient, suffix: str) -> RequestContext:
    person = RequestContext(
        user_id=f"suivi-{suffix}",
        email=f"{suffix}@example.org",
        roles=[],
        is_admin=False,
        first_name="Suivi",
        last_name=suffix,
    )
    app.dependency_overrides[get_current_user] = lambda: person
    try:
        client.get("/api/auth/me")
    finally:
        del app.dependency_overrides[get_current_user]
    return person


# --- Contenu d'une ligne ---


def test_row_carries_what_the_table_needs(client: TestClient, analyse: dict) -> None:
    dossier = _dossier(client, analyse, "Ligne complète")

    row = _track(client, analyse)["items"][0]

    assert row["id"] == dossier["id"] and row["name"] == "Ligne complète"
    assert row["analyse"] == {"id": analyse["id"], "name": analyse["name"]}
    assert row["status"]["is_initial"] is True
    assert row["assignee"] is None and row["due_at"] is None and row["due"] is None
    assert row["last_activity_at"] and row["created_at"]


def test_reference_is_readable_and_unique(client: TestClient, analyse: dict) -> None:
    _dossier(client, analyse, "Réf 1")
    _dossier(client, analyse, "Réf 2")

    references = [row["reference"] for row in _track(client, analyse)["items"]]

    assert len(set(references)) == 2
    assert all(ref.startswith("DOS-") and len(ref.split("-")) == 3 for ref in references)


def test_unassigned_dossiers_are_not_in_the_tracking(client: TestClient, analyse: dict) -> None:
    orphan = client.post("/api/dossiers", json={"name": "À ranger suivi"}).json()

    everywhere = client.get("/api/tracking", params={"search": "À ranger suivi"}).json()

    assert orphan["id"] not in [row["id"] for row in everywhere["items"]]


def test_due_level_follows_the_analyse_thresholds(client: TestClient, analyse: dict) -> None:
    dossier = _dossier(client, analyse, "Échéance suivi")
    client.put(f"/api/dossiers/{dossier['id']}/due-at", json={"due_at": _day(-2)})

    row = _track(client, analyse)["items"][0]

    assert row["due_at"] == _day(-2)
    assert row["due"]["level"] == "overdue" and row["due"]["days_left"] == -2 and row["due"]["color"]


# --- Filtres ---


def test_filters_by_analyse(client: TestClient, analyse: dict) -> None:
    other = client.post("/api/analyses", json={"name": f"Autre {uuid.uuid4().hex[:6]}", "description": "T"}).json()
    _dossier(client, analyse, "Dans A")
    _dossier(client, other, "Dans B")

    assert _names(client, analyse) == ["Dans A"]
    both = client.get("/api/tracking", params={"analyse_id": [analyse["id"], other["id"]], "page_size": 100}).json()
    assert {row["name"] for row in both["items"]} == {"Dans A", "Dans B"}


def test_filters_by_status_and_category(client: TestClient, analyse: dict) -> None:
    statuses = sorted(analyse["statuses"], key=lambda s: s["position"])
    final = next(s for s in statuses if s["is_final"])
    initial = next(s for s in statuses if s["is_initial"])
    open_one, closed = _dossier(client, analyse, "Ouvert"), _dossier(client, analyse, "Clos")
    client.put(f"/api/dossiers/{closed['id']}/workflow-status", json={"status_id": final["id"]})

    assert _names(client, analyse, status_id=final["id"]) == ["Clos"]
    assert _names(client, analyse, status_category="final") == ["Clos"]
    assert _names(client, analyse, status_category="initial") == ["Ouvert"]
    assert _names(client, analyse, status_id=initial["id"]) == ["Ouvert"]
    assert open_one["id"]


def test_filters_by_assignee(client: TestClient, analyse: dict) -> None:
    camille = _person(client, uuid.uuid4().hex[:6])
    mine, free = _dossier(client, analyse, "Affecté"), _dossier(client, analyse, "Libre")
    client.put(f"/api/dossiers/{mine['id']}/assignee", json={"assignee_id": camille.user_id})

    assert _names(client, analyse, assignee=camille.user_id) == ["Affecté"]
    assert _names(client, analyse, assignee="none") == ["Libre"]
    assert _track(client, analyse, assignee="none")["items"][0]["id"] == free["id"]
    assert _names(client, analyse, assignee="me") == []  # « moi » = dev-user, qui n'a rien


def test_filters_by_due(client: TestClient, analyse: dict) -> None:
    for name, offset in (("Dépassé", -3), ("Bientôt", 5), ("Loin", 25)):
        client.put(f"/api/dossiers/{_dossier(client, analyse, name)['id']}/due-at", json={"due_at": _day(offset)})
    _dossier(client, analyse, "Sans")

    assert _names(client, analyse, due="overdue") == ["Dépassé"]
    assert sorted(_names(client, analyse, due="7")) == ["Bientôt"]
    assert sorted(_names(client, analyse, due="30")) == ["Bientôt", "Loin"]
    assert _names(client, analyse, due="none") == ["Sans"]
    assert client.get("/api/tracking", params={"due": "demain"}).status_code == 422


def test_search_matches_name_and_reference(client: TestClient, analyse: dict) -> None:
    _dossier(client, analyse, "Association Les Mouettes")
    _dossier(client, analyse, "Convention culturelle")
    reference = _track(client, analyse, search="mouettes")["items"][0]["reference"]

    assert _names(client, analyse, search="MOUETTES") == ["Association Les Mouettes"]
    assert _names(client, analyse, search=reference) == ["Association Les Mouettes"]
    assert _names(client, analyse, search="100%") == []  # « % » n'est pas un joker


# --- Tri et pagination ---


def test_sorts_by_name_both_ways(client: TestClient, analyse: dict) -> None:
    for name in ("b-dossier", "C-dossier", "a-dossier"):
        _dossier(client, analyse, name)

    assert _names(client, analyse, sort="name", direction="asc") == ["a-dossier", "b-dossier", "C-dossier"]
    assert _names(client, analyse, sort="name", direction="desc") == ["C-dossier", "b-dossier", "a-dossier"]


def test_sort_by_due_keeps_missing_dates_last_in_both_directions(client: TestClient, analyse: dict) -> None:
    for name, offset in (("Tard", 20), ("Tôt", 2)):
        client.put(f"/api/dossiers/{_dossier(client, analyse, name)['id']}/due-at", json={"due_at": _day(offset)})
    _dossier(client, analyse, "Aucune")

    assert _names(client, analyse, sort="due", direction="asc") == ["Tôt", "Tard", "Aucune"]
    assert _names(client, analyse, sort="due", direction="desc") == ["Tard", "Tôt", "Aucune"]


def test_sort_by_assignee_puts_unassigned_last(client: TestClient, analyse: dict) -> None:
    person = _person(client, uuid.uuid4().hex[:6])
    client.put(
        f"/api/dossiers/{_dossier(client, analyse, 'Pris')['id']}/assignee", json={"assignee_id": person.user_id}
    )
    _dossier(client, analyse, "Libre")

    assert _names(client, analyse, sort="assignee", direction="asc") == ["Pris", "Libre"]
    assert _names(client, analyse, sort="assignee", direction="desc") == ["Pris", "Libre"]


def test_sort_by_reference_follows_creation_order(client: TestClient, analyse: dict) -> None:
    for name in ("Premier", "Deuxième", "Troisième"):
        _dossier(client, analyse, name)

    assert _names(client, analyse, sort="reference", direction="asc") == ["Premier", "Deuxième", "Troisième"]


def test_last_activity_ignores_consultations(client: TestClient, analyse: dict) -> None:
    dossier = _dossier(client, analyse, "Activité")
    before = _track(client, analyse)["items"][0]["last_activity_at"]

    client.get(f"/api/dossiers/{dossier['id']}")  # une consultation
    after_view = _track(client, analyse)["items"][0]["last_activity_at"]
    client.put(f"/api/dossiers/{dossier['id']}/due-at", json={"due_at": _day(3)})
    after_change = _track(client, analyse)["items"][0]["last_activity_at"]

    assert after_view == before
    assert after_change > before


def test_pagination_counts_the_whole_filtered_set(client: TestClient, analyse: dict) -> None:
    for i in range(5):
        _dossier(client, analyse, f"Page {i}")

    first = client.get(
        "/api/tracking", params={"analyse_id": analyse["id"], "page_size": 2, "sort": "reference", "direction": "asc"}
    ).json()
    last = client.get(
        "/api/tracking",
        params={"analyse_id": analyse["id"], "page_size": 2, "page": 3, "sort": "reference", "direction": "asc"},
    ).json()

    assert first["total"] == 5 and first["pages"] == 3 and len(first["items"]) == 2
    assert [row["name"] for row in last["items"]] == ["Page 4"]


def test_unknown_sort_key_is_rejected(client: TestClient) -> None:
    assert client.get("/api/tracking", params={"sort": "mot_de_passe"}).status_code == 422
    assert client.get("/api/tracking", params={"page_size": 101}).status_code == 422
