"""Catégories et messages des notifications (issue #174). Logique **pure** : aucun accès à la base."""

from typing import Literal

Kind = Literal["assigned", "due_soon", "overdue", "status_changed", "analysis_done", "analysis_failed", "reminder"]
Category = Literal["assignment", "deadline", "status", "analysis", "reminder"]

KIND_CATEGORY: dict[str, Category] = {
    "assigned": "assignment",
    "due_soon": "deadline",
    "overdue": "deadline",
    "status_changed": "status",
    "analysis_done": "analysis",
    "analysis_failed": "analysis",
    "reminder": "reminder",
}

CATEGORIES: tuple[Category, ...] = ("assignment", "deadline", "status", "analysis", "reminder")


def kinds_of(category: str) -> list[str]:
    return [kind for kind, cat in KIND_CATEGORY.items() if cat == category]


def _by(actor_name: str | None) -> str:
    return f" par {actor_name}" if actor_name else ""


def assigned_message(actor_name: str | None) -> str:
    return f"Ce dossier vous a été affecté{_by(actor_name)}."


def status_changed_message(new_status: str, actor_name: str | None) -> str:
    return f"Statut passé à « {new_status} »{_by(actor_name)}."


def analysis_message(failed: bool) -> str:
    return "L'analyse que vous avez lancée a échoué." if failed else "L'analyse que vous avez lancée est terminée."


def due_message(level: str, days_left: int) -> str:
    if level == "overdue":
        return "L'échéance du dossier est dépassée."
    if days_left == 0:
        return "L'échéance du dossier est aujourd'hui."
    return f"L'échéance du dossier approche : dans {days_left} j."
