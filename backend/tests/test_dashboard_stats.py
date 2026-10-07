"""Calculs purs du tableau de bord (issue #174) : semaines de Paris et messages d'activité."""

from datetime import UTC, date, datetime

from app.services.dashboard_stats import activity_message, bucket_by_week, week_start, week_windows


def test_week_starts_on_monday() -> None:
    assert week_start(date(2026, 10, 7)) == date(2026, 10, 5)  # mercredi → lundi
    assert week_start(date(2026, 10, 5)) == date(2026, 10, 5)  # un lundi
    assert week_start(date(2026, 10, 11)) == date(2026, 10, 5)  # dimanche → lundi précédent


def test_week_windows_are_four_consecutive_paris_weeks() -> None:
    windows = week_windows(date(2026, 10, 7))

    assert len(windows) == 4
    assert [end for _, end in windows[:-1]] == [start for start, _ in windows[1:]]  # sans trou ni chevauchement
    # Lundi 5 octobre 2026, 00 h à Paris (heure d'été, UTC+2) = dimanche 4 octobre, 22 h UTC.
    assert windows[-1][0] == datetime(2026, 10, 4, 22, 0, tzinfo=UTC)
    assert windows[0][0] == datetime(2026, 9, 13, 22, 0, tzinfo=UTC)


def test_week_windows_follow_the_clock_change() -> None:
    # Le 25 octobre 2026 on passe à l'heure d'hiver : la semaine du 26 commence à 23 h UTC la veille.
    windows = week_windows(date(2026, 10, 28), 2)

    assert windows[0][0] == datetime(2026, 10, 18, 22, 0, tzinfo=UTC)
    assert windows[1][0] == datetime(2026, 10, 25, 23, 0, tzinfo=UTC)


def test_sunday_evening_in_paris_belongs_to_that_week() -> None:
    windows = week_windows(date(2026, 10, 7))
    # Dimanche 4 octobre, 21 h 30 UTC = 23 h 30 à Paris : encore la semaine précédente.
    sunday = datetime(2026, 10, 4, 21, 30, tzinfo=UTC)
    # Lundi 5 octobre, 00 h 30 à Paris = dimanche 22 h 30 UTC : la semaine en cours.
    monday = datetime(2026, 10, 4, 22, 30, tzinfo=UTC)

    assert bucket_by_week([sunday, monday, monday], windows) == [0, 0, 1, 2]


def test_bucket_ignores_instants_outside_the_windows() -> None:
    windows = week_windows(date(2026, 10, 7))

    assert bucket_by_week([datetime(2026, 1, 1, tzinfo=UTC), datetime(2027, 1, 1, tzinfo=UTC)], windows) == [0, 0, 0, 0]


def test_status_change_message_names_both_statuses_and_the_author() -> None:
    payload = {"from": {"name": "À instruire"}, "to": {"name": "En instruction"}}

    assert activity_message("status_changed", payload, "Camille Durand") == (
        "Statut : À instruire → En instruction, par Camille Durand"
    )


def test_initial_status_message_has_no_previous_status() -> None:
    assert activity_message("status_changed", {"from": None, "to": {"name": "À instruire"}}, None) == (
        "Statut initial : À instruire"
    )


def test_other_messages() -> None:
    assert activity_message("document_added", {}, "Samir Benali") == "Document ajouté, par Samir Benali"
    assert activity_message("analysis_finished", {}, None) == "Analyse terminée"
    assert activity_message("analysis_failed", {}, None) == "L'analyse a échoué"
