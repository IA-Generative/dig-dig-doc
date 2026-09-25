from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.celery_client import celery_client
from app.core.security.factory import RequestContext, get_current_user

router = APIRouter(
    prefix="/admin/tasks", tags=["Admin"], dependencies=[Depends(get_current_user)]
)


def _require_admin(user: RequestContext) -> None:
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux administrateurs",
        )


@router.get("")
async def list_tasks(
    user: Annotated[RequestContext, Depends(get_current_user)],
) -> dict:
    """Introspection des tâches Celery (admin seulement).

    Retourne les tâches enregistrées, actives, réservées et planifiées
    via le canal de contrôle du broker. Pas de result backend configuré :
    seules les tâches vivantes (pas l'historique) sont visibles.
    """
    _require_admin(user)

    inspect = celery_client.control.inspect(timeout=3.0)

    registered = inspect.registered() or {}
    active = inspect.active() or {}
    reserved = inspect.reserved() or {}
    scheduled = inspect.scheduled() or {}

    # Liste des workers connus
    workers = list(
        registered.keys() | active.keys() | reserved.keys() | scheduled.keys()
    )

    return {
        "workers": sorted(workers),
        "registered": _flatten_tasks(registered),
        "active": _flatten_tasks(active),
        "reserved": _flatten_tasks(reserved),
        "scheduled": _flatten_tasks(scheduled),
    }


def _flatten_tasks(by_worker: dict) -> list[dict]:
    """Aplatit le dict {worker: [tasks]} en une liste plate de tâches
    avec le nom du worker associé."""
    result: list[dict] = []
    for worker, tasks in by_worker.items():
        if not isinstance(tasks, list):
            continue
        for task in tasks:
            if isinstance(task, dict):
                result.append(
                    {
                        "worker": worker,
                        "name": task.get("name") or task.get("type") or "unknown",
                        "id": task.get("id"),
                        "args": task.get("args"),
                        "kwargs": task.get("kwargs"),
                        "time_start": task.get("time_start"),
                        "acknowledged": task.get("acknowledged"),
                    }
                )
            elif isinstance(task, str):
                result.append({"worker": worker, "name": task})
    return result
