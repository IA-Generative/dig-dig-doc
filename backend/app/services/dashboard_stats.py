"""Calculs du tableau de bord (issue #174) : semaines civiles de Paris et messages d'activité.

Logique **pure** : « aujourd'hui » est un paramètre, ce qui rend chaque règle testable avec une date fixe."""

from collections.abc import Iterable
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from app.models.dossier_event import DossierEventType
from app.services.due_date import PARIS


def week_start(day: date) -> date:
    """Lundi de la semaine qui contient ``day``."""
    return day - timedelta(days=day.weekday())


def week_windows(today: date, weeks: int = 4) -> list[tuple[datetime, datetime]]:
    """Les ``weeks`` dernières semaines civiles de Paris, de la plus ancienne à la semaine en cours : chacune est
    l'intervalle ``[lundi 00 h, lundi suivant 00 h[`` (instants UTC)."""
    current = week_start(today)
    windows = []
    for back in range(weeks - 1, -1, -1):
        start = current - timedelta(weeks=back)
        windows.append(
            (
                datetime.combine(start, time.min, PARIS).astimezone(UTC),
                datetime.combine(start + timedelta(weeks=1), time.min, PARIS).astimezone(UTC),
            )
        )
    return windows


def bucket_by_week(instants: Iterable[datetime], windows: list[tuple[datetime, datetime]]) -> list[int]:
    """Nombre d'instants dans chaque fenêtre (ceux qui n'entrent dans aucune sont ignorés)."""
    return [sum(1 for instant in instants if start <= instant < end) for start, end in windows]


# Événements du journal montrés dans « activité récente », avec le type d'activité de l'interface.
ACTIVITY_KINDS: dict[str, str] = {
    DossierEventType.STATUS_CHANGED.value: "status_changed",
    DossierEventType.DOCUMENT_ADDED.value: "document_added",
    DossierEventType.ANALYSIS_FINISHED.value: "analysis_done",
    DossierEventType.ANALYSIS_FAILED.value: "analysis_failed",
}


def activity_message(event_type: str, payload: dict[str, Any], actor_name: str | None) -> str:
    """Phrase courte d'un événement d'activité ; l'auteur est nommé quand c'est une personne."""
    if event_type == DossierEventType.STATUS_CHANGED.value:
        before = (payload.get("from") or {}).get("name")
        after = (payload.get("to") or {}).get("name", "")
        text = f"Statut : {before} → {after}" if before else f"Statut initial : {after}"
    elif event_type == DossierEventType.DOCUMENT_ADDED.value:
        # Le journal ne garde pas le nom des fichiers (données d'usagers).
        text = "Document ajouté"
    elif event_type == DossierEventType.ANALYSIS_FINISHED.value:
        text = "Analyse terminée"
    else:
        text = "L'analyse a échoué"
    return f"{text}, par {actor_name}" if actor_name else text
