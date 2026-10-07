import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.factory import RequestContext, get_current_user
from app.db import get_db
from app.models.dossier import Dossier
from app.repositories.work_slot_repository import WorkSlotRepository
from app.schemas.work_slot import SlotIn, SlotOut

# Créneaux de traitement (issue #174) : **privés**, chacun ne voit et ne modifie que les siens. Toujours rattachés
# à un dossier ; un seul par personne et par dossier.
router = APIRouter(tags=["Créneaux"], dependencies=[Depends(get_current_user)])


@router.get("/slots", response_model=list[SlotOut])
async def list_my_slots(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
) -> list[SlotOut]:
    """Mes créneaux, par début."""
    return [SlotOut.model_validate(slot) for slot in await WorkSlotRepository(db).list_for(user.user_id)]


@router.put("/dossiers/{dossier_id}/slot", response_model=SlotOut)
async def put_my_slot(
    dossier_id: uuid.UUID,
    body: SlotIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
) -> SlotOut:
    """Pose mon créneau sur ce dossier, ou remplace le précédent."""
    if await db.get(Dossier, dossier_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dossier introuvable")
    return SlotOut.model_validate(await WorkSlotRepository(db).upsert(user.user_id, dossier_id, body))


@router.delete("/dossiers/{dossier_id}/slot", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_slot(
    dossier_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
) -> Response:
    """Retire mon créneau de ce dossier (sans erreur s'il n'y en avait pas)."""
    await WorkSlotRepository(db).delete(user.user_id, dossier_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
