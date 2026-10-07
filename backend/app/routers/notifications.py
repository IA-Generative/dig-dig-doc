import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.factory import RequestContext, get_current_user
from app.db import get_db
from app.repositories.notification_repository import NotificationRepository
from app.schemas.notification import MarkedOut, NotificationOut, UnreadCountOut

# Notifications (issue #174) : **propres à la personne connectée**. Chaque lecture met d'abord à jour ses
# notifications à partir du journal et des échéances (voir NotificationRepository.sync), donc l'interrogation
# périodique de `unread-count` suffit à les faire apparaître.
router = APIRouter(prefix="/notifications", tags=["Notifications"], dependencies=[Depends(get_current_user)])

Category = Literal["assignment", "deadline", "status", "analysis", "reminder"]


@router.get("/unread-count", response_model=UnreadCountOut)
async def unread_count(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
) -> UnreadCountOut:
    """Nombre de non lues (pastille), au total et par catégorie."""
    repository = NotificationRepository(db)
    await repository.sync(user.user_id)
    total, by_category = await repository.unread_counts(user.user_id)
    return UnreadCountOut(total=total, by_category=by_category)


@router.get("", response_model=list[NotificationOut])
async def list_notifications(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
    category: Category | None = None,
    unread: Annotated[bool, Query(description="Seulement les non lues")] = False,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[NotificationOut]:
    """Mes notifications, de la plus récente à la plus ancienne."""
    repository = NotificationRepository(db)
    await repository.sync(user.user_id)
    items = await repository.list_for(user.user_id, category=category, unread_only=unread, limit=limit)
    return [NotificationOut.model_validate(item) for item in items]


@router.post("/read-all", response_model=MarkedOut)
async def read_all(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
    category: Category | None = None,
) -> MarkedOut:
    """Marque comme lues toutes mes notifications (ou celles d'une catégorie)."""
    repository = NotificationRepository(db)
    await repository.sync(user.user_id)  # ce qui vient d'arriver est lu aussi
    return MarkedOut(marked=await repository.mark_all_read(user.user_id, category))


@router.post("/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def read_one(
    notification_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
) -> None:
    """Marque une de mes notifications comme lue ; 404 si elle n'existe pas ou n'est pas à moi."""
    if not await NotificationRepository(db).mark_read(user.user_id, notification_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification introuvable")
