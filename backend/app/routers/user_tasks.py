"""Router pour les tâches utilisateur (issue #62).

Expose les endpoints permettant à l'utilisateur de consulter ses tâches
asynchrones (Celery) en cours et terminées. Les tâches sont créées au
moment du dispatch (côté routers backend) et mises à jour par les workers
via le router interne.
"""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.factory import RequestContext, get_current_user
from app.db import get_db
from app.models.user_task import UserTaskStatus
from app.schemas.user_task import UserTaskOut
from app.services.user_task_service import get_task, get_user_tasks

router = APIRouter(prefix="/me/tasks", tags=["User Tasks"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[UserTaskOut])
async def list_my_tasks(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
    task_status: Annotated[UserTaskStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[UserTaskOut]:
    """Liste les tâches de l'utilisateur courant, triées par date de
    création décroissante. Filtrage optionnel par statut."""
    tasks = await get_user_tasks(db, user.user_id, status=task_status, limit=limit)
    return [UserTaskOut.model_validate(t) for t in tasks]


@router.get("/{task_id}", response_model=UserTaskOut)
async def get_my_task(
    task_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
) -> UserTaskOut:
    """Récupère une tâche par son ID. 404 si la tâche n'existe pas ou
    n'appartient pas à l'utilisateur."""
    task = await get_task(db, task_id, user.user_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tâche introuvable")
    return UserTaskOut.model_validate(task)
