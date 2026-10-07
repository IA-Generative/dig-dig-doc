"""Occurrences d'un créneau (issue #219) : les règles de répétition, les cas limites de calendrier et d'heure."""

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest

from app.services.slot_occurrences import MAX_OCCURRENCES, occurrence_starts

PARIS = ZoneInfo("Europe/Paris")
FOREVER = datetime(2100, 1, 1, tzinfo=UTC)
LONG_AGO = datetime(2000, 1, 1, tzinfo=UTC)


def paris(year: int, month: int, day: int, hour: int = 9, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=PARIS)


def local_days(occurrences: list[datetime]) -> list[tuple[int, int, int]]:
    return [(o.astimezone(PARIS).year, o.astimezone(PARIS).month, o.astimezone(PARIS).day) for o in occurrences]


def never() -> dict:
    return {"type": "never"}


def run(start: datetime, recurrence: dict | None, window_to: datetime = FOREVER, window_from: datetime = LONG_AGO):
    return occurrence_starts(start, recurrence, window_from, window_to)


# --- Sans récurrence ---


def test_a_single_slot_has_one_occurrence_inside_the_window() -> None:
    start = paris(2026, 10, 8)

    assert run(start, None) == [start]
    assert run(start, None, window_from=paris(2026, 10, 9)) == []
    assert run(start, None, window_to=paris(2026, 10, 7)) == []
    assert run(start, None, window_from=start, window_to=start) == [start]  # bornes incluses


# --- Jour ---


def test_daily_every_two_days() -> None:
    result = run(paris(2026, 10, 1), {"unit": "day", "interval": 2, "end": {"type": "count", "count": 4}})

    assert local_days(result) == [(2026, 10, 1), (2026, 10, 3), (2026, 10, 5), (2026, 10, 7)]


def test_the_count_includes_the_first_slot() -> None:
    result = run(paris(2026, 10, 1), {"unit": "day", "interval": 1, "end": {"type": "count", "count": 1}})

    assert len(result) == 1


def test_until_is_inclusive_through_the_end_of_that_day() -> None:
    recurrence = {"unit": "day", "interval": 1, "end": {"type": "until", "date": "2026-10-03"}}

    assert local_days(run(paris(2026, 10, 1), recurrence)) == [(2026, 10, 1), (2026, 10, 2), (2026, 10, 3)]


def test_until_accepts_a_date_object() -> None:
    recurrence = {"unit": "day", "interval": 1, "end": {"type": "until", "date": date(2026, 10, 2)}}

    assert len(run(paris(2026, 10, 1), recurrence)) == 2


def test_the_window_filters_without_changing_the_series() -> None:
    recurrence = {"unit": "day", "interval": 1, "end": never()}

    result = run(paris(2026, 10, 1), recurrence, window_from=paris(2026, 10, 5), window_to=paris(2026, 10, 7, 23))

    assert local_days(result) == [(2026, 10, 5), (2026, 10, 6), (2026, 10, 7)]


# --- Semaine ---


def test_weekly_defaults_to_the_weekday_of_the_first_slot() -> None:
    # Jeudi 8 octobre 2026 : toutes les semaines, le jeudi.
    result = run(paris(2026, 10, 8), {"unit": "week", "interval": 1, "end": {"type": "count", "count": 3}})

    assert local_days(result) == [(2026, 10, 8), (2026, 10, 15), (2026, 10, 22)]


def test_weekly_on_chosen_days_never_goes_before_the_first_slot() -> None:
    # Départ le jeudi 8 : lundi (0) et jeudi (3) ; le lundi 5 de la même semaine est avant le départ.
    recurrence = {"unit": "week", "interval": 1, "weekdays": [3, 0], "end": {"type": "count", "count": 4}}

    assert local_days(run(paris(2026, 10, 8), recurrence)) == [
        (2026, 10, 8),
        (2026, 10, 12),
        (2026, 10, 15),
        (2026, 10, 19),
    ]


def test_every_two_weeks() -> None:
    recurrence = {"unit": "week", "interval": 2, "weekdays": [0, 3], "end": {"type": "count", "count": 4}}

    assert local_days(run(paris(2026, 10, 5), recurrence)) == [
        (2026, 10, 5),
        (2026, 10, 8),
        (2026, 10, 19),
        (2026, 10, 22),
    ]


# --- Mois et année : quantièmes qui n'existent pas ---


def test_monthly_on_the_31st_falls_back_to_the_last_day_and_comes_back() -> None:
    result = run(paris(2026, 1, 31), {"unit": "month", "interval": 1, "end": {"type": "count", "count": 4}})

    # février : 28 ; mars retrouve le 31 (le quantième d'origine, pas le dernier jour de février)
    assert local_days(result) == [(2026, 1, 31), (2026, 2, 28), (2026, 3, 31), (2026, 4, 30)]


def test_monthly_in_a_leap_year() -> None:
    result = run(paris(2024, 1, 31), {"unit": "month", "interval": 1, "end": {"type": "count", "count": 2}})

    assert local_days(result) == [(2024, 1, 31), (2024, 2, 29)]


def test_monthly_every_three_months_across_a_year_end() -> None:
    result = run(paris(2026, 11, 15), {"unit": "month", "interval": 3, "end": {"type": "count", "count": 3}})

    assert local_days(result) == [(2026, 11, 15), (2027, 2, 15), (2027, 5, 15)]


def test_yearly_on_february_29th() -> None:
    result = run(paris(2024, 2, 29), {"unit": "year", "interval": 1, "end": {"type": "count", "count": 5}})

    assert local_days(result) == [(2024, 2, 29), (2025, 2, 28), (2026, 2, 28), (2027, 2, 28), (2028, 2, 29)]


# --- Heure d'été et d'hiver ---


def test_a_daily_slot_keeps_its_wall_clock_hour_across_the_clock_change() -> None:
    # Le dimanche 25 octobre 2026 on passe à l'heure d'hiver : 9 h reste 9 h à Paris (7 h UTC puis 8 h UTC).
    result = run(paris(2026, 10, 24), {"unit": "day", "interval": 1, "end": {"type": "count", "count": 3}})

    assert [o.astimezone(PARIS).hour for o in result] == [9, 9, 9]
    assert [o.hour for o in result] == [7, 8, 8]  # UTC


def test_the_spring_change_does_not_shift_the_local_hour() -> None:
    result = run(paris(2026, 3, 28), {"unit": "day", "interval": 1, "end": {"type": "count", "count": 3}})

    assert [o.astimezone(PARIS).hour for o in result] == [9, 9, 9]
    assert [o.hour for o in result] == [8, 7, 7]


def test_results_are_in_utc() -> None:
    assert all(
        o.tzinfo is not None and o.utcoffset().total_seconds() == 0
        for o in run(paris(2026, 10, 8), {"unit": "day", "interval": 1, "end": {"type": "count", "count": 2}})
    )


# --- Garde-fous ---


def test_the_series_is_capped() -> None:
    result = run(paris(2020, 1, 1), {"unit": "day", "interval": 1, "end": never()})

    assert len(result) == MAX_OCCURRENCES


def test_an_empty_window_gives_nothing() -> None:
    recurrence = {"unit": "day", "interval": 1, "end": never()}

    assert run(paris(2026, 10, 1), recurrence, window_from=paris(2026, 10, 5), window_to=paris(2026, 10, 4)) == []


@pytest.mark.parametrize("unit", ["day", "week", "month", "year"])
def test_every_unit_yields_the_first_slot_first(unit: str) -> None:
    start = paris(2026, 10, 8)  # un jeudi

    result = run(start, {"unit": unit, "interval": 1, "end": {"type": "count", "count": 2}})

    assert result[0] == start.astimezone(UTC)
