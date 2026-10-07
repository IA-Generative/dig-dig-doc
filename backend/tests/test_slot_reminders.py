"""Rappels de créneau côté serveur (issue #219) : une notification par occurrence et par décalage, sans doublon."""

import uuid
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from app.db import async_session_factory
from app.models.work_slot import WorkSlot
from app.repositories.notification_repository import REMINDER_WINDOW_HOURS, NotificationRepository
from tests.access_support import As
from tests.test_dossier_access import _create

PARIS = ZoneInfo("Europe/Paris")
# Un jeudi à 9 h, heure de Paris (heure d'été : 7 h UTC).
START = datetime(2026, 10, 8, 9, 0, tzinfo=PARIS)
LONG_BEFORE = START - timedelta(days=30)


def _add_slot(client: TestClient, person, dossier_id: str, **fields) -> None:
    async def go() -> None:
        async with async_session_factory() as db:
            db.add(
                WorkSlot(
                    id=uuid.uuid4(),
                    user_id=person.user_id,
                    dossier_id=uuid.UUID(dossier_id),
                    start_at=fields.get("start", START),
                    end_at=fields.get("start", START) + timedelta(hours=1),
                    recurrence=fields.get("recurrence"),
                    reminders=fields.get("reminders", []),
                    # Par défaut le créneau a été posé bien avant : tous ses rappels sont éligibles.
                    updated_at=fields.get("registered_at", LONG_BEFORE),
                )
            )
            await db.commit()

    client.portal.call(go)


def _sync(client: TestClient, person, now: datetime) -> list[dict]:
    """Met à jour les notifications de la personne « à `now` » et renvoie ses rappels."""

    async def go() -> list[dict]:
        async with async_session_factory() as db:
            repository = NotificationRepository(db)
            await repository.sync(person, now)
            items = await repository.list_for(person.user_id, category="reminder")
            return [
                {"message": n.message, "key": n.dedup_key, "at": n.created_at, "dossier": n.dossier_id} for n in items
            ]

    return client.portal.call(go)


def _dossier(client: TestClient, analyse: dict, world: dict) -> dict:
    with As(world["alice"]):
        return _create(client, analyse)


# --- Un créneau unique ---


def test_a_due_reminder_is_created_once(client: TestClient, analyse: dict, world: dict) -> None:
    dossier = _dossier(client, analyse, world)
    _add_slot(client, world["alice"], dossier["id"], reminders=[15])
    now = START - timedelta(minutes=10)  # le rappel de 15 minutes est passé de 5 minutes

    first = _sync(client, world["alice"], now)
    again = _sync(client, world["alice"], now + timedelta(minutes=1))

    assert len(first) == 1 and first[0]["message"] == "Rappel : créneau de traitement à 09:00."
    assert first[0]["at"] == START - timedelta(minutes=15)  # datée de l'heure du rappel
    assert [r["key"] for r in again] == [r["key"] for r in first]  # relire ne duplique pas


def test_a_reminder_that_is_not_due_yet_is_not_created(client: TestClient, analyse: dict, world: dict) -> None:
    dossier = _dossier(client, analyse, world)
    _add_slot(client, world["alice"], dossier["id"], reminders=[15])

    assert _sync(client, world["alice"], START - timedelta(minutes=20)) == []


def test_an_old_reminder_is_not_replayed(client: TestClient, analyse: dict, world: dict) -> None:
    dossier = _dossier(client, analyse, world)
    _add_slot(client, world["alice"], dossier["id"], reminders=[15])

    just_inside = START - timedelta(minutes=15) + timedelta(hours=REMINDER_WINDOW_HOURS) - timedelta(minutes=1)
    too_late = START - timedelta(minutes=15) + timedelta(hours=REMINDER_WINDOW_HOURS) + timedelta(minutes=1)

    assert len(_sync(client, world["alice"], just_inside)) == 1
    other = _dossier(client, analyse, world)
    _add_slot(client, world["alice"], other["id"], reminders=[15])
    assert [r for r in _sync(client, world["alice"], too_late) if r["dossier"] == uuid.UUID(other["id"])] == []


def test_no_reminder_for_an_instant_before_the_slot_was_saved(client: TestClient, analyse: dict, world: dict) -> None:
    dossier = _dossier(client, analyse, world)
    # Posé à 8 h 55 pour 9 h avec un rappel 15 minutes avant (8 h 45) : cet instant est déjà passé.
    _add_slot(client, world["alice"], dossier["id"], reminders=[15, 0], registered_at=START - timedelta(minutes=5))

    result = _sync(client, world["alice"], START + timedelta(minutes=1))

    assert [r["at"] for r in result] == [START]  # seul le rappel « à l'heure » reste


def test_several_reminders_each_get_a_notification(client: TestClient, analyse: dict, world: dict) -> None:
    dossier = _dossier(client, analyse, world)
    _add_slot(client, world["alice"], dossier["id"], reminders=[0, 15, 60])

    result = _sync(client, world["alice"], START + timedelta(minutes=1))

    assert sorted(r["at"] for r in result) == [START - timedelta(minutes=60), START - timedelta(minutes=15), START]
    assert len({r["key"] for r in result}) == 3


def test_a_slot_without_reminders_produces_nothing(client: TestClient, analyse: dict, world: dict) -> None:
    dossier = _dossier(client, analyse, world)
    _add_slot(client, world["alice"], dossier["id"], reminders=[])

    assert _sync(client, world["alice"], START + timedelta(minutes=1)) == []


# --- Créneau récurrent ---


def test_each_occurrence_of_a_recurring_slot_reminds_once(client: TestClient, analyse: dict, world: dict) -> None:
    dossier = _dossier(client, analyse, world)
    recurrence = {"unit": "day", "interval": 1, "end": {"type": "count", "count": 3}}
    _add_slot(client, world["alice"], dossier["id"], recurrence=recurrence, reminders=[30])

    day2 = START + timedelta(days=1) - timedelta(minutes=20)  # 8 h 40 le lendemain : le rappel de 8 h 30 est passé
    day3 = START + timedelta(days=2) - timedelta(minutes=20)
    after_day2 = _sync(client, world["alice"], day2)
    after_day3 = _sync(client, world["alice"], day3)
    after_the_end = _sync(client, world["alice"], START + timedelta(days=5))  # la série est finie : rien de plus

    # Le premier jour est trop ancien (hors fenêtre) : on ne rejoue pas un rappel de la veille.
    assert [r["at"] for r in after_day2] == [START + timedelta(days=1) - timedelta(minutes=30)]
    assert len(after_day3) == 2 and len({r["key"] for r in after_day3}) == 2
    assert len(after_the_end) == len(after_day3)


def test_a_recurring_reminder_follows_the_clock_change(client: TestClient, analyse: dict, world: dict) -> None:
    dossier = _dossier(client, analyse, world)
    saturday = datetime(2026, 10, 24, 9, 0, tzinfo=PARIS)  # le dimanche 25, l'heure d'hiver : 9 h reste 9 h
    recurrence = {"unit": "day", "interval": 1, "end": {"type": "count", "count": 2}}
    _add_slot(client, world["alice"], dossier["id"], start=saturday, recurrence=recurrence, reminders=[0])

    result = _sync(client, world["alice"], datetime(2026, 10, 25, 9, 1, tzinfo=PARIS))

    assert [r["message"] for r in result] == ["Rappel : créneau de traitement à 09:00."]
    assert result[0]["at"] == datetime(2026, 10, 25, 9, 0, tzinfo=PARIS)  # 8 h UTC, pas 7 h


# --- Propriétaire et accès ---


def test_a_reminder_is_only_for_the_owner_of_the_slot(client: TestClient, analyse: dict, world: dict) -> None:
    dossier = _dossier(client, analyse, world)
    _add_slot(client, world["alice"], dossier["id"], reminders=[0])
    now = START + timedelta(minutes=1)

    assert _sync(client, world["carol"], now) == []  # carol voit le dossier, mais le créneau est à alice
    assert len(_sync(client, world["alice"], now)) == 1


def test_no_reminder_for_a_dossier_i_can_no_longer_see(client: TestClient, analyse: dict, world: dict) -> None:
    dossier = _dossier(client, analyse, world)
    _add_slot(client, world["alice"], dossier["id"], reminders=[0])
    left = type(world["alice"])(**{**world["alice"].__dict__, "groups": ["/ailleurs"]})

    assert _sync(client, left, START + timedelta(minutes=1)) == []


# --- Par l'API ---


def test_a_slot_saved_through_the_api_does_not_remind_for_the_past(
    client: TestClient, analyse: dict, world: dict
) -> None:
    dossier = _dossier(client, analyse, world)
    soon = datetime.now(UTC) + timedelta(minutes=3)
    with As(world["alice"]):
        saved = client.put(
            f"/api/dossiers/{dossier['id']}/slot",
            json={"start": soon.isoformat(), "end": (soon + timedelta(hours=1)).isoformat(), "reminders": [5, 60]},
        )
        notifications = client.get("/api/notifications", params={"category": "reminder"}).json()
        counts = client.get("/api/notifications/unread-count").json()

    assert saved.status_code == 200
    assert notifications == []  # les rappels de 5 et 60 minutes avant précèdent la pose du créneau
    assert counts["by_category"]["reminder"] == 0


def test_replacing_a_slot_restarts_the_reminder_clock(client: TestClient, analyse: dict, world: dict) -> None:
    dossier = _dossier(client, analyse, world)
    far = datetime.now(UTC) + timedelta(days=1)
    with As(world["alice"]):
        first = client.put(
            f"/api/dossiers/{dossier['id']}/slot",
            json={"start": far.isoformat(), "end": (far + timedelta(hours=1)).isoformat(), "reminders": [0]},
        ).json()
        second = client.put(
            f"/api/dossiers/{dossier['id']}/slot",
            json={"start": far.isoformat(), "end": (far + timedelta(hours=1)).isoformat(), "reminders": [0, 5]},
        ).json()

    assert second["id"] == first["id"] and second["updated_at"] > first["updated_at"]
