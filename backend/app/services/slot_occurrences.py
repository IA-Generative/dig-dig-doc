"""Occurrences d'un créneau de traitement (issue #219) : développe la règle de répétition en débuts d'occurrence.

Logique **pure** (aucun accès à la base, aucune horloge) : elle reproduit celle de l'interface
(`frontend/src/utils/recurrence.ts`), pour que le serveur et l'agenda voient les mêmes occurrences.

- Les calculs se font en **heure locale de Paris** : une occurrence garde la même heure de l'horloge d'un jour à
  l'autre, même quand l'heure change (un créneau de 9 h reste à 9 h, soit 7 h ou 8 h UTC selon la saison).
- Le premier créneau est la première occurrence ; « après N fois » le compte ; « jusqu'au » est **inclus** jusqu'à
  23 h 59 ce jour-là.
- Un quantième qui n'existe pas dans le mois est ramené à son dernier jour (31 janvier + 1 mois : 28 ou 29 février ;
  29 février + 1 an : 28 février), **depuis le quantième d'origine** : mars retrouve le 31.
- Garde-fou : jamais plus de 5 000 occurrences depuis le début de la série.
"""

import calendar
from collections.abc import Iterator
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from app.services.due_date import PARIS

MAX_OCCURRENCES = 5000


def _at(day: date, clock: time) -> datetime:
    """Instant (UTC) de ce jour à cette heure de Paris."""
    return datetime.combine(day, clock, PARIS).astimezone(UTC)


def _days_in_month(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def _generate(start: datetime, recurrence: dict[str, Any]) -> Iterator[datetime]:
    local = start.astimezone(PARIS)
    day, clock = local.date(), local.time().replace(tzinfo=None)
    interval = max(1, int(recurrence["interval"]))
    unit = recurrence["unit"]

    if unit == "day":
        k = 0
        while True:
            yield _at(day + timedelta(days=k * interval), clock)
            k += 1
    elif unit == "week":
        weekdays = sorted(recurrence.get("weekdays") or [day.weekday()])
        monday = day - timedelta(days=day.weekday())
        week = 0
        while True:
            for weekday in weekdays:
                occurrence = _at(monday + timedelta(weeks=week * interval, days=weekday), clock)
                if occurrence >= start:  # la semaine de départ ne remonte pas avant le premier créneau
                    yield occurrence
            week += 1
    elif unit == "month":
        k = 0
        while True:
            year, month0 = divmod(day.year * 12 + day.month - 1 + k * interval, 12)
            month = month0 + 1
            if year > 9999:
                return
            yield _at(date(year, month, min(day.day, _days_in_month(year, month))), clock)
            k += 1
    else:  # year
        k = 0
        while True:
            year = day.year + k * interval
            if year > 9999:
                return
            yield _at(date(year, day.month, min(day.day, _days_in_month(year, day.month))), clock)
            k += 1


def occurrence_starts(
    start: datetime, recurrence: dict[str, Any] | None, window_from: datetime, window_to: datetime
) -> list[datetime]:
    """Débuts d'occurrence (UTC) compris entre ``window_from`` et ``window_to`` inclus, dans l'ordre. Sans récurrence,
    le créneau n'a qu'une occurrence : son début."""
    if recurrence is None:
        return [start] if window_from <= start <= window_to else []

    end = recurrence.get("end", {"type": "never"})
    until: datetime | None = None
    if end["type"] == "until":
        last_day = date.fromisoformat(end["date"]) if isinstance(end["date"], str) else end["date"]
        until = _at(last_day, time(23, 59, 59))
    max_count = end["count"] if end["type"] == "count" else None

    found: list[datetime] = []
    for index, occurrence in enumerate(_generate(start, recurrence)):
        if (max_count is not None and index >= max_count) or index >= MAX_OCCURRENCES:
            break
        if (until is not None and occurrence > until) or occurrence > window_to:
            break
        if occurrence >= window_from:
            found.append(occurrence)
    return found
