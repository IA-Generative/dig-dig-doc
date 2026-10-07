import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dossier_guard import require_dossier_visible
from app.core.security.factory import RequestContext, get_current_user
from app.db import get_db
from app.models.dossier import Dossier
from app.models.dossier_event import DossierEventType
from app.repositories.dossier_event_repository import DossierEventRepository
from app.schemas.dossier_event import DossierEventActorOut, DossierEventOut
from app.schemas.pagination import Page

# Journal d'événements d'un dossier (issue #169) : **lecture seule**. Aucune route de création, de
# modification ou de suppression n'existe : les événements ne sont écrits que par les actions du serveur.
router = APIRouter(
    prefix="/dossiers",
    tags=["Journal du dossier"],
    dependencies=[Depends(get_current_user), Depends(require_dossier_visible)],
)


@router.get("/{dossier_id}/events/actors", response_model=list[DossierEventActorOut])
async def list_dossier_event_actors(
    dossier_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
) -> list[DossierEventActorOut]:
    """Auteurs ayant agi sur le dossier, par nom (filtre « Auteur » de l'historique). Les actions du système n'y
    figurent pas."""
    if await db.get(Dossier, dossier_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dossier introuvable")
    actors = await DossierEventRepository(db).list_actors(dossier_id, include_admin_access=user.is_admin)
    return [DossierEventActorOut(actor_id=actor_id, actor_name=name) for actor_id, name in actors]


@router.get("/{dossier_id}/events", response_model=Page[DossierEventOut])
async def list_dossier_events(
    dossier_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    type: Annotated[list[DossierEventType] | None, Query(description="Un ou plusieurs types d'événements")] = None,
    actor_id: Annotated[str | None, Query(description="Identifiant de l'auteur")] = None,
) -> Page[DossierEventOut]:
    """Événements du dossier, du plus récent au plus ancien, paginés, filtrables par type et par auteur."""
    if await db.get(Dossier, dossier_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dossier introuvable")
    events, total = await DossierEventRepository(db).list_paginated(
        dossier_id,
        page=page,
        page_size=page_size,
        types=type,
        actor_id=actor_id,
        include_admin_access=user.is_admin,
    )
    return Page.of([DossierEventOut.model_validate(e) for e in events], total=total, page=page, page_size=page_size)
