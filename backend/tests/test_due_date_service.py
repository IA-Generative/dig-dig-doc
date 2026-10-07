"""Calcul d'échéance (issue #172) : logique pure, sans base ni horloge."""

from datetime import UTC, date, datetime

import pytest

from app.services.due_date import (
    DEFAULT_THRESHOLDS,
    DueInfo,
    closed_before_due,
    due_info,
    normalize_thresholds,
    today_in_paris,
)

TODAY = date(2026, 10, 7)
FAR = DEFAULT_THRESHOLDS["far_color"]
ORANGE = DEFAULT_THRESHOLDS["steps"][0]["color"]
RED = DEFAULT_THRESHOLDS["steps"][1]["color"]
OVERDUE = DEFAULT_THRESHOLDS["overdue_color"]


def _info(days_from_today: int, **kwargs) -> DueInfo | None:
    due = date.fromordinal(TODAY.toordinal() + days_from_today)
    return due_info(due, DEFAULT_THRESHOLDS, TODAY, **kwargs)


def test_no_due_date_means_no_info() -> None:
    assert due_info(None, DEFAULT_THRESHOLDS, TODAY) is None


@pytest.mark.parametrize(
    ("days", "level", "color"),
    [
        (365, "ok", FAR),
        (31, "ok", FAR),  # juste au-delà du premier seuil
        (30, "soon", ORANGE),  # un seuil de 30 jours couvre « 30 jours ou moins »
        (8, "soon", ORANGE),
        (7, "soon", RED),  # le seuil le plus serré qui contient la date gagne
        (1, "soon", RED),
        (0, "soon", RED),  # c'est aujourd'hui : pas encore dépassé
        (-1, "overdue", OVERDUE),
        (-400, "overdue", OVERDUE),
    ],
)
def test_level_and_color_follow_the_thresholds(days: int, level: str, color: str) -> None:
    assert _info(days) == DueInfo(level, days, color)


def test_days_left_is_negative_when_overdue() -> None:
    assert _info(-3).days_left == -3


def test_a_closed_dossier_is_no_longer_watched_and_has_no_color() -> None:
    assert _info(-10, closed=True) == DueInfo("closed", -10, None)
    assert _info(5, closed=True) == DueInfo("closed", 5, None)


def test_custom_thresholds_are_used() -> None:
    thresholds = {
        "far_color": "#111111",
        "steps": [{"days": 90, "color": "#222222"}, {"days": 14, "color": "#333333"}, {"days": 3, "color": "#444444"}],
        "overdue_color": "#555555",
    }
    due = lambda days: due_info(date.fromordinal(TODAY.toordinal() + days), thresholds, TODAY).color  # noqa: E731

    assert [due(d) for d in (200, 90, 15, 14, 4, 3, 0, -1)] == [
        "#111111",
        "#222222",
        "#222222",
        "#333333",
        "#333333",
        "#444444",
        "#444444",
        "#555555",
    ]


def test_thresholds_without_steps_only_distinguish_far_and_overdue() -> None:
    thresholds = {"far_color": "#111111", "steps": [], "overdue_color": "#555555"}

    assert due_info(date(2026, 10, 8), thresholds, TODAY) == DueInfo("ok", 1, "#111111")
    assert due_info(date(2026, 10, 6), thresholds, TODAY) == DueInfo("overdue", -1, "#555555")


def test_steps_given_in_any_order_give_the_same_result() -> None:
    reversed_steps = {**DEFAULT_THRESHOLDS, "steps": list(reversed(DEFAULT_THRESHOLDS["steps"]))}
    due = date(2026, 10, 12)  # dans 5 jours

    assert due_info(due, reversed_steps, TODAY) == due_info(due, DEFAULT_THRESHOLDS, TODAY)


def test_normalize_thresholds_sorts_steps_from_widest_to_tightest() -> None:
    shuffled = {**DEFAULT_THRESHOLDS, "steps": [{"days": 7, "color": RED}, {"days": 30, "color": ORANGE}]}
    assert [s["days"] for s in normalize_thresholds(shuffled)["steps"]] == [30, 7]


def test_the_default_thresholds_are_already_sorted() -> None:
    assert normalize_thresholds(DEFAULT_THRESHOLDS) == DEFAULT_THRESHOLDS


# --- Clos avant l'échéance ---


@pytest.mark.parametrize(
    ("closed_at", "expected"),
    [
        (datetime(2026, 10, 5, 12, 0, tzinfo=UTC), True),  # avant
        (datetime(2026, 10, 7, 9, 0, tzinfo=UTC), True),  # le jour même
        (datetime(2026, 10, 8, 9, 0, tzinfo=UTC), False),  # le lendemain
    ],
)
def test_closed_before_due(closed_at: datetime, expected: bool) -> None:
    assert closed_before_due(closed_at, date(2026, 10, 7)) is expected


def test_closed_before_due_uses_the_paris_calendar_day() -> None:
    due = date(2026, 10, 7)
    # 22h30 UTC le 7 octobre = 00h30 le 8 à Paris (heure d'été) : clos le lendemain de l'échéance.
    assert closed_before_due(datetime(2026, 10, 7, 22, 30, tzinfo=UTC), due) is False
    # 21h30 UTC le 7 = 23h30 le 7 à Paris : encore le jour de l'échéance.
    assert closed_before_due(datetime(2026, 10, 7, 21, 30, tzinfo=UTC), due) is True


def test_closed_before_due_is_unknown_without_closure_or_due_date() -> None:
    assert closed_before_due(None, date(2026, 10, 7)) is None
    assert closed_before_due(datetime(2026, 10, 5, tzinfo=UTC), None) is None


def test_today_in_paris_follows_the_french_calendar_day() -> None:
    assert today_in_paris(datetime(2026, 10, 7, 22, 30, tzinfo=UTC)) == date(2026, 10, 8)
    assert today_in_paris(datetime(2026, 1, 7, 22, 30, tzinfo=UTC)) == date(2026, 1, 7)  # heure d'hiver : UTC+1
