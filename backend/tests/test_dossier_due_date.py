"""Échéance des dossiers (issue #172) : date, durée par défaut, seuils de couleur, filtre et tri."""

import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.services.due_date import DEFAULT_THRESHOLDS, today_in_paris


def _day(offset: int) -> str:
    return (today_in_paris() + timedelta(days=offset)).isoformat()


def _create_analyse(client: TestClient, name: str = "Échéance") -> dict:
    return client.post("/api/analyses", json={"name": name, "description": "Test"}).json()


def _create_dossier(client: TestClient, analyse_id: str | None, name: str = "Dossier échéance") -> dict:
    payload = {"name": name}
    if analyse_id:
        payload["analyse_id"] = analyse_id
    return client.post("/api/dossiers", json=payload).json()


def _set_due(client: TestClient, dossier_id: str, due_at: str | None):
    return client.put(f"/api/dossiers/{dossier_id}/due-at", json={"due_at": due_at})


def _put_settings(client: TestClient, analyse_id: str, default_due_days, thresholds: dict):
    return client.put(
        f"/api/analyses/{analyse_id}/due-settings",
        json={"default_due_days": default_due_days, "thresholds": thresholds},
    )


def _list(client: TestClient, **params) -> list[dict]:
    """Tous les dossiers de la liste (toutes les pages) : la base de test en contient beaucoup d'autres."""
    items: list[dict] = []
    page = 1
    while True:
        body = client.get("/api/dossiers", params={"page": page, "page_size": 100, **params}).json()
        items += body["items"]
        if page >= body["pages"]:
            return items
        page += 1


# --- Échéance d'un dossier ---


def test_new_dossier_has_no_due_date_by_default(client: TestClient) -> None:
    dossier = _create_dossier(client, _create_analyse(client)["id"])

    assert dossier["due_at"] is None and dossier["due"] is None and dossier["closed_before_due"] is None


def test_due_date_can_be_set_changed_and_removed(client: TestClient) -> None:
    dossier = _create_dossier(client, _create_analyse(client)["id"])

    set_ = _set_due(client, dossier["id"], _day(10)).json()
    changed = _set_due(client, dossier["id"], _day(3)).json()
    removed = _set_due(client, dossier["id"], None).json()

    assert set_["due_at"] == _day(10) and set_["due"]["days_left"] == 10
    assert changed["due_at"] == _day(3) and changed["due"]["days_left"] == 3
    assert removed["due_at"] is None and removed["due"] is None


def test_due_info_is_computed_by_the_server_from_the_analyse_thresholds(client: TestClient) -> None:
    analyse = _create_analyse(client)
    dossier = _create_dossier(client, analyse["id"])
    orange = DEFAULT_THRESHOLDS["steps"][0]["color"]
    red = DEFAULT_THRESHOLDS["steps"][1]["color"]

    far = _set_due(client, dossier["id"], _day(60)).json()["due"]
    soon = _set_due(client, dossier["id"], _day(20)).json()["due"]
    critical = _set_due(client, dossier["id"], _day(2)).json()["due"]
    overdue = _set_due(client, dossier["id"], _day(-4)).json()["due"]

    assert far == {"level": "ok", "days_left": 60, "color": DEFAULT_THRESHOLDS["far_color"]}
    assert soon == {"level": "soon", "days_left": 20, "color": orange}
    assert critical == {"level": "soon", "days_left": 2, "color": red}
    assert overdue == {"level": "overdue", "days_left": -4, "color": DEFAULT_THRESHOLDS["overdue_color"]}


def test_changing_the_thresholds_changes_the_level_of_existing_dossiers(client: TestClient) -> None:
    analyse = _create_analyse(client)
    dossier = _create_dossier(client, analyse["id"])
    _set_due(client, dossier["id"], _day(60))
    assert client.get(f"/api/dossiers/{dossier['id']}").json()["due"]["level"] == "ok"

    _put_settings(
        client,
        analyse["id"],
        None,
        {"far_color": "#111111", "steps": [{"days": 90, "color": "#222222"}], "overdue_color": "#333333"},
    )

    due = client.get(f"/api/dossiers/{dossier['id']}").json()["due"]
    assert due == {"level": "soon", "days_left": 60, "color": "#222222"}


def test_dossier_without_analyse_can_have_a_due_date_with_the_default_thresholds(client: TestClient) -> None:
    dossier = _create_dossier(client, None, "À ranger")

    due = _set_due(client, dossier["id"], _day(2)).json()["due"]

    assert due["level"] == "soon" and due["color"] == DEFAULT_THRESHOLDS["steps"][1]["color"]


def test_invalid_due_date_is_rejected_and_unknown_dossier_is_404(client: TestClient) -> None:
    dossier = _create_dossier(client, _create_analyse(client)["id"])

    assert _set_due(client, dossier["id"], "pas-une-date").status_code == 422
    assert _set_due(client, str(uuid.uuid4()), _day(1)).status_code == 404


# --- Clôture ---


def test_a_closed_dossier_is_no_longer_watched(client: TestClient) -> None:
    analyse = _create_analyse(client)
    final = next(s for s in analyse["statuses"] if s["is_final"])
    dossier = _create_dossier(client, analyse["id"])
    _set_due(client, dossier["id"], _day(-5))

    closed = client.put(f"/api/dossiers/{dossier['id']}/workflow-status", json={"status_id": final["id"]}).json()

    assert closed["due"] == {"level": "closed", "days_left": -5, "color": None}


def test_closed_before_due_is_exposed(client: TestClient) -> None:
    analyse = _create_analyse(client)
    initial = next(s for s in analyse["statuses"] if s["is_initial"])
    final = next(s for s in analyse["statuses"] if s["is_final"])
    on_time = _create_dossier(client, analyse["id"], "Dans les temps")
    late = _create_dossier(client, analyse["id"], "En retard")
    _set_due(client, on_time["id"], _day(5))
    _set_due(client, late["id"], _day(-1))

    closed_on_time = client.put(
        f"/api/dossiers/{on_time['id']}/workflow-status", json={"status_id": final["id"]}
    ).json()
    closed_late = client.put(f"/api/dossiers/{late['id']}/workflow-status", json={"status_id": final["id"]}).json()
    reopened = client.put(f"/api/dossiers/{on_time['id']}/workflow-status", json={"status_id": initial["id"]}).json()

    assert closed_on_time["closed_before_due"] is True
    assert closed_late["closed_before_due"] is False
    assert reopened["closed_before_due"] is None  # rouvert : la question ne se pose plus


def test_closed_before_due_is_unknown_without_a_due_date(client: TestClient) -> None:
    analyse = _create_analyse(client)
    final = next(s for s in analyse["statuses"] if s["is_final"])
    dossier = _create_dossier(client, analyse["id"])

    closed = client.put(f"/api/dossiers/{dossier['id']}/workflow-status", json={"status_id": final["id"]}).json()

    assert closed["due"] is None and closed["closed_before_due"] is None


# --- Durée par défaut ---


def test_default_duration_gives_an_due_date_to_new_dossiers(client: TestClient) -> None:
    analyse = _create_analyse(client)
    _put_settings(client, analyse["id"], 45, DEFAULT_THRESHOLDS)

    dossier = _create_dossier(client, analyse["id"])

    assert dossier["due_at"] == _day(45)
    created = client.get(f"/api/dossiers/{dossier['id']}/events", params={"type": "created"}).json()["items"][0]
    assert created["payload"]["due_at"] == _day(45)


def test_default_duration_applies_to_a_dossier_assigned_later_only_if_it_has_no_due_date(client: TestClient) -> None:
    analyse = _create_analyse(client)
    _put_settings(client, analyse["id"], 30, DEFAULT_THRESHOLDS)
    plain = _create_dossier(client, None, "Sans échéance")
    dated = _create_dossier(client, None, "Avec échéance")
    _set_due(client, dated["id"], _day(2))

    assigned_plain = client.post(f"/api/dossiers/{plain['id']}/assign", json={"analyse_id": analyse["id"]}).json()
    assigned_dated = client.post(f"/api/dossiers/{dated['id']}/assign", json={"analyse_id": analyse["id"]}).json()

    assert assigned_plain["due_at"] == _day(30)
    assert assigned_dated["due_at"] == _day(2)  # une échéance déjà fixée n'est pas écrasée
    event = client.get(f"/api/dossiers/{plain['id']}/events", params={"type": "due_date_changed"}).json()["items"][0]
    assert event["payload"] == {"from": None, "to": _day(30), "reason": "default_duration"}


def test_no_default_duration_means_no_automatic_due_date(client: TestClient) -> None:
    analyse = _create_analyse(client)
    _put_settings(client, analyse["id"], None, DEFAULT_THRESHOLDS)
    assert _create_dossier(client, analyse["id"])["due_at"] is None


# --- Réglages de l'analyse ---


def test_new_analyse_has_the_default_due_settings(client: TestClient) -> None:
    analyse = _create_analyse(client)

    assert analyse["due_settings"] == {"default_due_days": None, "thresholds": DEFAULT_THRESHOLDS}
    assert analyse["due_settings_versions"] == []
    assert client.get(f"/api/analyses/{analyse['id']}/due-settings").json() == analyse["due_settings"]


def test_steps_are_sorted_from_the_widest_to_the_tightest(client: TestClient) -> None:
    analyse = _create_analyse(client)
    thresholds = {
        "far_color": "#111111",
        "steps": [{"days": 3, "color": "#333333"}, {"days": 21, "color": "#222222"}],
        "overdue_color": "#444444",
    }

    saved = _put_settings(client, analyse["id"], 20, thresholds).json()["due_settings"]

    assert [s["days"] for s in saved["thresholds"]["steps"]] == [21, 3]
    assert saved["default_due_days"] == 20


@pytest.mark.parametrize(
    "thresholds",
    [
        {"far_color": "vert", "steps": [], "overdue_color": "#000000"},  # couleur invalide
        {"far_color": "#111111", "steps": [{"days": 0, "color": "#222222"}], "overdue_color": "#000000"},  # jours < 1
        {
            "far_color": "#111111",
            "steps": [{"days": 7, "color": "#222222"}, {"days": 7, "color": "#333333"}],
            "overdue_color": "#000000",
        },  # seuils en double
        {
            "far_color": "#111111",
            "steps": [{"days": d, "color": "#222222"} for d in (1, 2, 3, 4, 5, 6)],
            "overdue_color": "#000000",
        },  # plus de 5 seuils
    ],
)
def test_invalid_thresholds_are_rejected(client: TestClient, thresholds: dict) -> None:
    analyse = _create_analyse(client)
    assert _put_settings(client, analyse["id"], None, thresholds).status_code == 422


@pytest.mark.parametrize("days", [0, -3, 4000])
def test_invalid_default_duration_is_rejected(client: TestClient, days: int) -> None:
    analyse = _create_analyse(client)
    assert _put_settings(client, analyse["id"], days, DEFAULT_THRESHOLDS).status_code == 422


def test_due_settings_are_versioned_and_restorable(client: TestClient) -> None:
    analyse = _create_analyse(client)
    custom = {"far_color": "#111111", "steps": [{"days": 14, "color": "#222222"}], "overdue_color": "#333333"}

    updated = _put_settings(client, analyse["id"], 60, custom).json()
    versions = updated["due_settings_versions"]
    assert len(versions) == 1
    assert versions[0]["content"] == {"default_due_days": None, "thresholds": DEFAULT_THRESHOLDS}

    restored = client.post(f"/api/analyses/{analyse['id']}/due-settings/restore/{versions[0]['id']}").json()

    assert restored["due_settings"] == {"default_due_days": None, "thresholds": DEFAULT_THRESHOLDS}
    assert len(restored["due_settings_versions"]) == 2  # l'état personnalisé est lui-même devenu une version


def test_unchanged_due_settings_do_not_create_a_version(client: TestClient) -> None:
    analyse = _create_analyse(client)
    saved = _put_settings(client, analyse["id"], None, DEFAULT_THRESHOLDS).json()
    assert saved["due_settings_versions"] == []


def test_restore_unknown_due_settings_version_is_404(client: TestClient) -> None:
    analyse = _create_analyse(client)
    assert client.post(f"/api/analyses/{analyse['id']}/due-settings/restore/{uuid.uuid4()}").status_code == 404


# --- Journal ---


def test_due_date_changes_are_recorded_in_the_journal(client: TestClient) -> None:
    dossier = _create_dossier(client, _create_analyse(client)["id"])

    _set_due(client, dossier["id"], _day(10))
    _set_due(client, dossier["id"], _day(10))  # inchangée : rien de plus
    _set_due(client, dossier["id"], _day(4))
    _set_due(client, dossier["id"], None)

    events = client.get(f"/api/dossiers/{dossier['id']}/events", params={"type": "due_date_changed"}).json()["items"]
    assert [(e["payload"]["from"], e["payload"]["to"]) for e in events] == [
        (_day(4), None),
        (_day(10), _day(4)),
        (None, _day(10)),
    ]
    assert events[0]["actor_id"] == "dev-user"


# --- Filtre et tri ---


def test_list_can_be_filtered_by_due_date(client: TestClient) -> None:
    analyse = _create_analyse(client)
    final = next(s for s in analyse["statuses"] if s["is_final"])
    late = _create_dossier(client, analyse["id"], "En retard")
    week = _create_dossier(client, analyse["id"], "Cette semaine")
    month = _create_dossier(client, analyse["id"], "Ce mois-ci")
    none = _create_dossier(client, analyse["id"], "Sans échéance")
    closed_late = _create_dossier(client, analyse["id"], "Clos en retard")
    for dossier, offset in ((late, -3), (week, 5), (month, 20), (closed_late, -9)):
        _set_due(client, dossier["id"], _day(offset))
    client.put(f"/api/dossiers/{closed_late['id']}/workflow-status", json={"status_id": final["id"]})

    ours = {late["id"], week["id"], month["id"], none["id"], closed_late["id"]}
    ids = lambda **p: {d["id"] for d in _list(client, **p)} & ours  # noqa: E731

    assert ids(due="overdue") == {late["id"]}  # un dossier clos n'est pas « en retard »
    assert ids(due="7") == {week["id"]}
    assert ids(due="30") == {week["id"], month["id"]}
    assert ids(due="none") == {none["id"]}


def test_list_can_be_sorted_by_due_date_with_undated_dossiers_last(client: TestClient) -> None:
    analyse = _create_analyse(client)
    later = _create_dossier(client, analyse["id"], "Plus tard")
    sooner = _create_dossier(client, analyse["id"], "Plus tôt")
    none = _create_dossier(client, analyse["id"], "Sans échéance")
    _set_due(client, later["id"], _day(300))
    _set_due(client, sooner["id"], _day(250))

    ids = [d["id"] for d in _list(client, sort="due")]

    assert ids.index(sooner["id"]) < ids.index(later["id"]) < ids.index(none["id"])


def test_unknown_due_filter_is_rejected(client: TestClient) -> None:
    assert client.get("/api/dossiers", params={"due": "demain"}).status_code == 422
