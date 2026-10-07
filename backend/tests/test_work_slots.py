"""Créneaux de traitement (issue #174) : privés, rattachés à un dossier, validés, joints aux urgences."""

import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.security.factory import RequestContext, get_current_user
from app.main import app
from app.services.due_date import today_in_paris


def _person(suffix: str) -> RequestContext:
    return RequestContext(
        user_id=f"crn-{suffix}",
        email=f"{suffix}@example.org",
        roles=[],
        is_admin=False,
        first_name="Créneau",
        last_name=suffix,
        groups=["/dev-tests"],
    )


@pytest.fixture
def me(client: TestClient):
    person = _person(uuid.uuid4().hex[:8])
    app.dependency_overrides[get_current_user] = lambda: person
    client.get("/api/auth/me")
    yield person
    del app.dependency_overrides[get_current_user]


@pytest.fixture
def dossier(client: TestClient, me) -> dict:
    analyse = client.post("/api/analyses", json={"name": f"Créneaux {uuid.uuid4().hex[:6]}", "description": "T"}).json()
    return client.post("/api/dossiers", json={"name": "Dossier à planifier", "analyse_id": analyse["id"]}).json()


def _slot(**overrides) -> dict:
    day = (today_in_paris() + timedelta(days=1)).isoformat()
    body = {"start": f"{day}T09:00:00+02:00", "end": f"{day}T10:30:00+02:00", "reminders": []}
    return {**body, **overrides}


def _put(client: TestClient, dossier_id: str, body: dict):
    return client.put(f"/api/dossiers/{dossier_id}/slot", json=body)


# --- Poser, remplacer, retirer ---


def test_put_creates_a_slot_and_returns_it(client: TestClient, dossier: dict) -> None:
    response = _put(client, dossier["id"], _slot(reminders=[15, 0]))

    assert response.status_code == 200
    slot = response.json()
    assert slot["dossier_id"] == dossier["id"] and slot["recurrence"] is None
    assert slot["reminders"] == [0, 15]  # rangés, sans doublon
    assert client.get("/api/slots").json() == [slot]


def test_put_replaces_the_previous_slot_of_the_dossier(client: TestClient, dossier: dict) -> None:
    first = _put(client, dossier["id"], _slot()).json()

    second = _put(client, dossier["id"], _slot(reminders=[30])).json()

    assert second["id"] == first["id"] and second["reminders"] == [30]
    assert len(client.get("/api/slots").json()) == 1  # un seul créneau par dossier


def test_delete_removes_the_slot_and_is_idempotent(client: TestClient, dossier: dict) -> None:
    _put(client, dossier["id"], _slot())

    assert client.delete(f"/api/dossiers/{dossier['id']}/slot").status_code == 204
    assert client.delete(f"/api/dossiers/{dossier['id']}/slot").status_code == 204
    assert client.get("/api/slots").json() == []


def test_a_slot_needs_an_existing_dossier(client: TestClient, me) -> None:
    assert _put(client, str(uuid.uuid4()), _slot()).status_code == 404


def test_slots_are_listed_by_start(client: TestClient, dossier: dict, me) -> None:
    other = client.post("/api/dossiers", json={"name": "Autre", "analyse_id": dossier["analyse_id"]}).json()
    late = _put(client, dossier["id"], _slot(start="2030-01-02T14:00:00+01:00", end="2030-01-02T15:00:00+01:00")).json()
    early = _put(client, other["id"], _slot(start="2030-01-02T09:00:00+01:00", end="2030-01-02T10:00:00+01:00")).json()

    assert [s["id"] for s in client.get("/api/slots").json()] == [early["id"], late["id"]]


# --- Privé ---


def test_a_slot_is_private_to_its_owner(client: TestClient, dossier: dict, me) -> None:
    mine = _put(client, dossier["id"], _slot()).json()
    other = _person(uuid.uuid4().hex[:8])

    app.dependency_overrides[get_current_user] = lambda: other
    try:
        assert client.get("/api/slots").json() == []
        # Poser le sien ne touche pas celui de l'autre ; supprimer « le sien » non plus.
        theirs = _put(client, dossier["id"], _slot(reminders=[5])).json()
        client.delete(f"/api/dossiers/{dossier['id']}/slot")
    finally:
        app.dependency_overrides[get_current_user] = lambda: me

    assert theirs["id"] != mine["id"]
    assert [s["id"] for s in client.get("/api/slots").json()] == [mine["id"]]


# --- Récurrence ---


def test_recurrence_is_stored_and_returned(client: TestClient, dossier: dict) -> None:
    recurrence = {"unit": "week", "interval": 2, "weekdays": [4, 0, 0], "end": {"type": "count", "count": 6}}

    slot = _put(client, dossier["id"], _slot(recurrence=recurrence)).json()

    assert slot["recurrence"] == {
        "unit": "week",
        "interval": 2,
        "weekdays": [0, 4],
        "end": {"type": "count", "count": 6},
    }


@pytest.mark.parametrize(
    "recurrence",
    [
        {"unit": "day", "interval": 0, "end": {"type": "never"}},
        {"unit": "day", "interval": 1000, "end": {"type": "never"}},
        {"unit": "fortnight", "interval": 1, "end": {"type": "never"}},
        {"unit": "day", "interval": 1, "weekdays": [1], "end": {"type": "never"}},
        {"unit": "week", "interval": 1, "weekdays": [7], "end": {"type": "never"}},
        {"unit": "day", "interval": 1, "end": {"type": "count", "count": 0}},
        {"unit": "day", "interval": 1, "end": {"type": "count", "count": 1001}},
        {"unit": "day", "interval": 1, "end": {"type": "forever"}},
        {"unit": "day", "interval": 1},
    ],
)
def test_invalid_recurrence_is_refused(client: TestClient, dossier: dict, recurrence: dict) -> None:
    assert _put(client, dossier["id"], _slot(recurrence=recurrence)).status_code == 422


def test_recurrence_cannot_end_before_the_first_slot(client: TestClient, dossier: dict) -> None:
    yesterday = (today_in_paris() - timedelta(days=1)).isoformat()

    response = _put(
        client,
        dossier["id"],
        _slot(recurrence={"unit": "day", "interval": 1, "end": {"type": "until", "date": yesterday}}),
    )

    assert response.status_code == 422


def test_recurrence_may_end_the_day_of_the_first_slot(client: TestClient, dossier: dict) -> None:
    day = (today_in_paris() + timedelta(days=1)).isoformat()

    response = _put(
        client, dossier["id"], _slot(recurrence={"unit": "day", "interval": 1, "end": {"type": "until", "date": day}})
    )

    assert response.status_code == 200


# --- Horaires et rappels ---


@pytest.mark.parametrize(
    "overrides",
    [
        {"end": "2030-01-02T08:00:00+01:00", "start": "2030-01-02T09:00:00+01:00"},  # fin avant le début
        {"end": "2030-01-02T09:00:00+01:00", "start": "2030-01-02T09:00:00+01:00"},  # durée nulle
        {"start": "2030-01-02T09:00:00+01:00", "end": "2030-01-03T10:00:00+01:00"},  # plus de 24 h
        {"start": "2030-01-02T09:00:00", "end": "2030-01-02T10:00:00"},  # sans fuseau
        {"reminders": [1, 2, 3, 4]},
        {"reminders": [-1]},
        {"reminders": [60 * 24 * 60 + 1]},
    ],
)
def test_invalid_times_and_reminders_are_refused(client: TestClient, dossier: dict, overrides: dict) -> None:
    assert _put(client, dossier["id"], _slot(**overrides)).status_code == 422


def test_exactly_24_hours_and_three_reminders_are_allowed(client: TestClient, dossier: dict) -> None:
    body = _slot(start="2030-01-02T09:00:00+01:00", end="2030-01-03T09:00:00+01:00", reminders=[0, 15, 10080])

    assert _put(client, dossier["id"], body).status_code == 200


# --- Tableau de bord ---


def test_dashboard_urgencies_carry_my_slot_only(client: TestClient, dossier: dict, me) -> None:
    client.put(f"/api/dossiers/{dossier['id']}/assignee", json={"assignee_id": me.user_id})
    client.put(
        f"/api/dossiers/{dossier['id']}/due-at", json={"due_at": (today_in_paris() + timedelta(days=2)).isoformat()}
    )
    assert client.get("/api/dashboard").json()["urgencies"][0]["slot"] is None

    mine = _put(client, dossier["id"], _slot(reminders=[15])).json()

    assert client.get("/api/dashboard").json()["urgencies"][0]["slot"] == mine
