"""Notifications (issue #174) : fabriquées à la lecture depuis le journal et les échéances, propres au destinataire."""

import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.security.factory import RequestContext, get_current_user
from app.main import app
from app.services.due_date import today_in_paris
from tests.test_dossier_events import INTERNAL_HEADERS


def _person(label: str) -> RequestContext:
    suffix = uuid.uuid4().hex[:8]
    return RequestContext(
        user_id=f"ntf-{suffix}",
        email=f"{suffix}@example.org",
        roles=[],
        is_admin=False,
        first_name=label,
        last_name=suffix,
    )


class As:
    """Exécute des appels « en tant que » une personne, puis revient à la précédente."""

    def __init__(self, person: RequestContext):
        self.person = person

    def __enter__(self):
        self.previous = app.dependency_overrides.get(get_current_user)
        app.dependency_overrides[get_current_user] = lambda: self.person
        return self.person

    def __exit__(self, *exc):
        if self.previous is None:
            del app.dependency_overrides[get_current_user]
        else:
            app.dependency_overrides[get_current_user] = self.previous


@pytest.fixture
def alice(client: TestClient) -> RequestContext:
    person = _person("Alice")
    with As(person):
        client.get("/api/auth/me")  # connue de l'annuaire : on peut lui affecter un dossier
    return person


@pytest.fixture
def bob(client: TestClient) -> RequestContext:
    person = _person("Bob")
    with As(person):
        client.get("/api/auth/me")
    return person


@pytest.fixture
def analyse(client: TestClient) -> dict:
    created = client.post("/api/analyses", json={"name": f"Notif {uuid.uuid4().hex[:6]}", "description": "T"}).json()
    return client.get(f"/api/analyses/{created['id']}").json()


def _dossier(client: TestClient, analyse: dict, name: str = "Dossier notifié") -> dict:
    return client.post("/api/dossiers", json={"name": name, "analyse_id": analyse["id"]}).json()


def _assign(client: TestClient, dossier: dict, person: RequestContext) -> None:
    client.put(f"/api/dossiers/{dossier['id']}/assignee", json={"assignee_id": person.user_id})


def _mine(client: TestClient, **params) -> list[dict]:
    return client.get("/api/notifications", params=params).json()


def _unread(client: TestClient) -> dict:
    return client.get("/api/notifications/unread-count").json()


# --- Affectation ---


def test_assigned_by_someone_else_notifies(client: TestClient, analyse: dict, alice, bob) -> None:
    dossier = _dossier(client, analyse)
    with As(alice):
        client.get("/api/notifications")  # premier passage : le curseur est posé
    with As(bob):
        _assign(client, dossier, alice)

    with As(alice):
        (notification,) = _mine(client)

    assert notification["kind"] == "assigned" and notification["category"] == "assignment"
    assert notification["dossier_id"] == dossier["id"] and notification["dossier_name"] == "Dossier notifié"
    assert (
        notification["message"] == f"Ce dossier vous a été affecté par Bob {bob.last_name}."
        and notification["read_at"] is None
    )


def test_assigning_to_yourself_does_not_notify(client: TestClient, analyse: dict, alice) -> None:
    with As(alice):
        client.get("/api/notifications")
        _assign(client, _dossier(client, analyse), alice)

        assert _mine(client) == []


def test_the_author_is_not_notified_but_the_assignee_is(client: TestClient, analyse: dict, alice, bob) -> None:
    dossier = _dossier(client, analyse)
    with As(alice):
        client.get("/api/notifications")
    with As(bob):
        client.get("/api/notifications")
        _assign(client, dossier, alice)
        assert _mine(client) == []  # Bob est l'auteur : rien pour lui


# --- Statut ---


def test_status_changed_by_someone_else_notifies_the_assignee(client: TestClient, analyse: dict, alice, bob) -> None:
    dossier = _dossier(client, analyse)
    _assign(client, dossier, alice)
    with As(alice):
        client.get("/api/notifications")
    final = next(s for s in analyse["statuses"] if s["is_final"])

    with As(bob):
        client.put(f"/api/dossiers/{dossier['id']}/workflow-status", json={"status_id": final["id"]})
    with As(alice):
        (notification,) = _mine(client, category="status")

    assert notification["kind"] == "status_changed"
    assert notification["message"] == f"Statut passé à « {final['name']} » par Bob {bob.last_name}."


def test_my_own_status_change_does_not_notify_me(client: TestClient, analyse: dict, alice) -> None:
    dossier = _dossier(client, analyse)
    _assign(client, dossier, alice)
    final = next(s for s in analyse["statuses"] if s["is_final"])
    with As(alice):
        client.get("/api/notifications")
        client.put(f"/api/dossiers/{dossier['id']}/workflow-status", json={"status_id": final["id"]})

        assert _mine(client, category="status") == []


def test_status_change_on_someone_elses_dossier_does_not_notify_me(
    client: TestClient, analyse: dict, alice, bob
) -> None:
    dossier = _dossier(client, analyse)  # affecté à personne
    final = next(s for s in analyse["statuses"] if s["is_final"])
    with As(alice):
        client.get("/api/notifications")
    with As(bob):
        client.put(f"/api/dossiers/{dossier['id']}/workflow-status", json={"status_id": final["id"]})

    with As(alice):
        assert _mine(client) == []


# --- Analyse ---


def _finish(client: TestClient, dossier: dict, status: str) -> None:
    launched = client.get(f"/api/dossiers/{dossier['id']}").json()
    for step in launched["execution_steps"]:
        client.post(
            f"/api/internal/execution-steps/{step['id']}/complete",
            json={"status": status, "output": "ok"},
            headers=INTERNAL_HEADERS,
        )


@pytest.mark.parametrize(("outcome", "kind"), [("terminé", "analysis_done"), ("échec", "analysis_failed")])
def test_the_person_who_launched_the_analysis_is_notified_of_its_end(
    client: TestClient, analyse: dict, alice, bob, outcome: str, kind: str
) -> None:
    dossier = _dossier(client, analyse)
    with As(alice):
        client.get("/api/notifications")
        client.post(f"/api/dossiers/{dossier['id']}/launch")
    _finish(client, dossier, outcome)

    with As(alice):
        (notification,) = _mine(client, category="analysis")
    with As(bob):
        assert _mine(client) == []  # Bob n'a rien lancé

    assert notification["kind"] == kind


# --- Échéance ---


def _set_due(client: TestClient, dossier: dict, offset: int) -> None:
    client.put(
        f"/api/dossiers/{dossier['id']}/due-at",
        json={"due_at": (today_in_paris() + timedelta(days=offset)).isoformat()},
    )


def test_entering_a_due_level_notifies_once_per_level(client: TestClient, analyse: dict, alice) -> None:
    dossier = _dossier(client, analyse)
    _assign(client, dossier, alice)
    with As(alice):
        client.get("/api/notifications")  # premier passage
        _set_due(client, dossier, 5)

        first = _mine(client, category="deadline")
        again = _mine(client, category="deadline")  # relire ne duplique pas
        _set_due(client, dossier, -2)
        later = _mine(client, category="deadline")

    assert [n["kind"] for n in first] == ["due_soon"] and first[0][
        "message"
    ] == "L'échéance du dossier approche : dans 5 j."
    assert [n["id"] for n in again] == [n["id"] for n in first]
    assert sorted(n["kind"] for n in later) == ["due_soon", "overdue"]


def test_a_far_or_closed_dossier_is_not_a_due_notification(client: TestClient, analyse: dict, alice) -> None:
    far, closed = _dossier(client, analyse, "Loin"), _dossier(client, analyse, "Clos")
    for dossier in (far, closed):
        _assign(client, dossier, alice)
    final = next(s for s in analyse["statuses"] if s["is_final"])
    with As(alice):
        client.get("/api/notifications")
        _set_due(client, far, 200)
        _set_due(client, closed, -5)
        client.put(f"/api/dossiers/{closed['id']}/workflow-status", json={"status_id": final["id"]})

        assert _mine(client, category="deadline") == []


def test_existing_urgencies_at_first_visit_are_recorded_as_read(client: TestClient, analyse: dict, alice) -> None:
    dossier = _dossier(client, analyse)
    _assign(client, dossier, alice)
    _set_due(client, dossier, -1)

    with As(alice):
        (notification,) = _mine(client, category="deadline")
        unread = _unread(client)

    assert notification["kind"] == "overdue" and notification["read_at"] is not None
    assert unread["by_category"]["deadline"] == 0  # l'agenda l'affiche déjà : pas de déluge


# --- Lecture, compteurs, marquage ---


def _two_notifications(client: TestClient, analyse: dict, alice, bob) -> tuple[dict, dict]:
    first, second = _dossier(client, analyse, "Un"), _dossier(client, analyse, "Deux")
    with As(alice):
        client.get("/api/notifications")
    with As(bob):
        _assign(client, first, alice)
        _assign(client, second, alice)
        final = next(s for s in analyse["statuses"] if s["is_final"])
        client.put(f"/api/dossiers/{second['id']}/workflow-status", json={"status_id": final["id"]})
    return first, second


def test_unread_counts_by_category(client: TestClient, analyse: dict, alice, bob) -> None:
    _two_notifications(client, analyse, alice, bob)

    with As(alice):
        counts = _unread(client)

    # Deux affectations, et le changement de statut du second dossier fait par Bob.
    assert counts == {
        "total": 3,
        "by_category": {"assignment": 2, "deadline": 0, "status": 1, "analysis": 0, "reminder": 0},
    }


def test_mark_one_read(client: TestClient, analyse: dict, alice, bob) -> None:
    _two_notifications(client, analyse, alice, bob)
    with As(alice):
        target = _mine(client)[0]

        assert client.post(f"/api/notifications/{target['id']}/read").status_code == 204
        assert client.post(f"/api/notifications/{target['id']}/read").status_code == 204  # idempotent

        assert _unread(client)["total"] == 2
        assert target["id"] not in [n["id"] for n in _mine(client, unread="true")]


def test_mark_all_read_by_category_or_everything(client: TestClient, analyse: dict, alice, bob) -> None:
    _two_notifications(client, analyse, alice, bob)
    with As(alice):
        assert client.post("/api/notifications/read-all", params={"category": "deadline"}).json() == {"marked": 0}
        assert client.post("/api/notifications/read-all", params={"category": "status"}).json() == {"marked": 1}
        assert client.post("/api/notifications/read-all").json() == {"marked": 2}
        assert _unread(client)["total"] == 0 and len(_mine(client)) == 3  # lues, pas supprimées


def test_notifications_are_private(client: TestClient, analyse: dict, alice, bob) -> None:
    _two_notifications(client, analyse, alice, bob)
    with As(alice):
        theirs = _mine(client)[0]

    with As(bob):
        assert _mine(client) == []
        assert client.post(f"/api/notifications/{theirs['id']}/read").status_code == 404
        assert client.post("/api/notifications/read-all").json() == {"marked": 0}
    with As(alice):
        assert _unread(client)["total"] == 3  # rien n'a bougé pour Alice


def test_unknown_notification_is_404_and_category_is_validated(client: TestClient, alice) -> None:
    with As(alice):
        assert client.post(f"/api/notifications/{uuid.uuid4()}/read").status_code == 404
        assert client.get("/api/notifications", params={"category": "autre"}).status_code == 422
        assert client.get("/api/notifications", params={"limit": 500}).status_code == 422


def test_history_before_the_first_visit_is_limited_to_a_week(client: TestClient, analyse: dict, alice, bob) -> None:
    # Un événement récent est repris au premier passage ; ceux d'avant la fenêtre ne le sont pas (voir la
    # constante FIRST_SYNC_DAYS) : on vérifie ici le cas « récent ».
    dossier = _dossier(client, analyse)
    with As(bob):
        _assign(client, dossier, alice)

    with As(alice):
        (notification,) = _mine(client)

    assert notification["kind"] == "assigned"
