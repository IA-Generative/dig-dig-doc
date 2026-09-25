"""Service de gestion des UserTask (issue #62).

Centralise la création et la mise à jour des lignes ``user_tasks`` pour
permettre le suivi des tâches asynchrones lancées par un utilisateur.

Deux points d'entrée :
- ``create_task`` : appelée par les routers backend juste après le dispatch
  Celery, pour persister la tâche avec son ``celery_task_id``.
- ``update_task`` : appelée par le router interne (callback worker) pour
  faire évoluer le statut (PENDING → RUNNING → SUCCESS/FAILURE).
"""
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_task import UserTask, UserTaskKind, UserTaskStatus
from app.schemas.user_task import UserTaskUpdateIn

# Libellés par défaut associés à chaque type de tâche.
_DEFAULT_LABELS: dict[UserTaskKind, str] = {
    UserTaskKind.TEXT_EXTRACTION: "Extraction de texte",
    UserTaskKind.CLASSIFICATION: "Classification documentaire",
    UserTaskKind.ENTITY_EXTRACTION: "Extraction d'entités",
    UserTaskKind.AGENT_EXECUTION: "Exécution des agents",
    UserTaskKind.CHAT_RESPONSE: "Réponse de l'assistant",
    UserTaskKind.HELPER_CHAT: "Réponse de l'agent helper",
    UserTaskKind.DOCUMENT_SUMMARY: "Résumé de document",
    UserTaskKind.DOSSIER_SUMMARY: "Résumé du dossier",
    UserTaskKind.ANALYSE_SUGGESTION: "Suggestions d'analyse",
}


async def create_task(
    db: AsyncSession,
    *,
    user_id: str,
    kind: UserTaskKind,
    celery_task_id: str | None = None,
    label: str | None = None,
    target_id: UUID | None = None,
    target_type: str | None = None,
) -> UserTask:
    """Crée et persiste une ligne ``user_tasks``.

    Appelée par les routers juste après ``dispatch_*`` pour mémoriser la
    tâche. Le ``celery_task_id`` permet ensuite au worker de mettre à jour
    la ligne via le callback interne.
    """
    task = UserTask(
        user_id=user_id,
        kind=kind,
        status=UserTaskStatus.PENDING,
        celery_task_id=celery_task_id,
        label=label or _DEFAULT_LABELS.get(kind, kind.value),
        target_id=target_id,
        target_type=target_type,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def update_task(
    db: AsyncSession,
    task_id: UUID,
    payload: UserTaskUpdateIn,
) -> UserTask | None:
    """Met à jour une tâche (statut, erreur, horodatages).

    Retourne la tâche mise à jour, ou ``None`` si elle n'existe pas.
    """
    values: dict = {"status": payload.status}
    if payload.error is not None:
        values["error"] = payload.error
    if payload.started_at is not None:
        values["started_at"] = payload.started_at
    if payload.ended_at is not None:
        values["ended_at"] = payload.ended_at

    stmt = update(UserTask).where(UserTask.id == task_id).values(**values).returning(UserTask)
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    await db.commit()
    return row


async def get_user_tasks(
    db: AsyncSession,
    user_id: str,
    *,
    status: UserTaskStatus | None = None,
    limit: int = 50,
) -> list[UserTask]:
    """Liste les tâches d'un utilisateur, triées par date de création
    décroissante (plus récentes d'abord). Optionnellement filtrées par
    statut."""
    stmt = select(UserTask).where(UserTask.user_id == user_id)
    if status is not None:
        stmt = stmt.where(UserTask.status == status)
    stmt = stmt.order_by(UserTask.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_task(db: AsyncSession, task_id: UUID, user_id: str) -> UserTask | None:
    """Récupère une tâche par son ID, en vérifiant qu'elle appartient bien
    à l'utilisateur."""
    stmt = select(UserTask).where(UserTask.id == task_id, UserTask.user_id == user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
