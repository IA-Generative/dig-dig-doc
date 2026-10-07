"""Échéance d'un dossier (issue #172) : niveau et couleur selon le temps restant, et « clos avant l'échéance ».

Logique **pure** : aucune dépendance à la base ni à l'horloge. « Aujourd'hui » est un paramètre, ce qui rend
chaque règle testable avec une date fixe. Le fuseau de référence est celui de Paris : une échéance est un
jour du calendrier, pas un instant.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, Literal
from zoneinfo import ZoneInfo

PARIS = ZoneInfo("Europe/Paris")

# Seuils donnés à toute nouvelle analyse : au-delà de 30 jours, vert ; de 30 à 8 jours, orange ; à 7 jours ou
# moins, rouge ; échéance dépassée, rouge foncé. L'administrateur les adapte ensuite par analyse.
DEFAULT_THRESHOLDS: dict[str, Any] = {
    "far_color": "#18753c",
    "steps": [
        {"days": 30, "color": "#b34000"},
        {"days": 7, "color": "#ce0500"},
    ],
    "overdue_color": "#8a0000",
}

Level = Literal["ok", "soon", "overdue", "closed"]


@dataclass(frozen=True)
class DueInfo:
    """Situation d'un dossier par rapport à son échéance.

    - ``ok`` : loin (au-delà du premier seuil) ;
    - ``soon`` : proche (dans un des seuils), la couleur est celle du seuil le plus serré qui contient la date ;
    - ``overdue`` : échéance dépassée ;
    - ``closed`` : le dossier est clos, l'échéance n'est plus à surveiller (pas de couleur).
    """

    level: Level
    days_left: int
    color: str | None


def today_in_paris(now: datetime | None = None) -> date:
    """Jour courant à Paris. ``now`` : instant à convertir (injectable dans les tests)."""
    return (now or datetime.now(UTC)).astimezone(PARIS).date()


def due_info(due_at: date | None, thresholds: dict[str, Any], today: date, *, closed: bool = False) -> DueInfo | None:
    """Niveau d'échéance d'un dossier, ou ``None`` s'il n'a pas d'échéance.

    Les seuils sont ``{"far_color", "steps": [{"days", "color"}, …], "overdue_color"}`` : un seuil de 30 jours
    couvre « 30 jours restants ou moins ». Un dossier clos n'a plus de couleur (``closed``).
    """
    if due_at is None:
        return None
    days_left = (due_at - today).days
    if closed:
        return DueInfo("closed", days_left, None)
    if days_left < 0:
        return DueInfo("overdue", days_left, thresholds["overdue_color"])

    # Seuils qui contiennent la date (jours restants <= seuil) : on garde le plus serré.
    containing = [step for step in thresholds["steps"] if days_left <= step["days"]]
    if not containing:
        return DueInfo("ok", days_left, thresholds["far_color"])
    tightest = min(containing, key=lambda step: step["days"])
    return DueInfo("soon", days_left, tightest["color"])


def closed_before_due(closed_at: datetime | None, due_at: date | None) -> bool | None:
    """Le dossier a-t-il été clos au plus tard le jour de son échéance ? ``None`` s'il n'est pas clos ou n'a
    pas d'échéance (la question ne se pose pas). Le jour de clôture est celui de Paris."""
    if closed_at is None or due_at is None:
        return None
    return closed_at.astimezone(PARIS).date() <= due_at


def normalize_thresholds(thresholds: dict[str, Any]) -> dict[str, Any]:
    """Seuils rangés du plus large au plus serré (30 j avant 7 j). Les règles de validité (jours positifs et
    distincts, couleurs) sont celles du schéma d'entrée de l'API."""
    return {
        "far_color": thresholds["far_color"],
        "steps": sorted(thresholds["steps"], key=lambda step: step["days"], reverse=True),
        "overdue_color": thresholds["overdue_color"],
    }
