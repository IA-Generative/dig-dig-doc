"""Travail à plusieurs sur l'analyse de dossier (issue #118, parent #106).

Verrou court par élément (avec expiration), présence en temps réel et flux SSE.
Internes : réservés aux instructeurs authentifiés, jamais exposés côté usager (#96)."""

import asyncio
import json
import uuid
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.factory import RequestContext, get_current_user
from app.db import async_session_factory, get_db
from app.repositories.analysis_collaboration_repository import (
    AnalysisCollaborationRepository,
    ElementLockedError,
    display_name,
    lock_out,
    settings,
)
from app.repositories.dossier_analysis_repository import DossierAnalysisRepository
from app.routers.dossier_analyses import _analysis_or_404, _ensure_editable
from app.schemas.analysis_collaboration import LiveSnapshot, LockOut, PresenceIn

router = APIRouter(prefix="/dossiers", tags=["Travail à plusieurs"], dependencies=[Depends(get_current_user)])

_BASE = "/{dossier_id}/analyses-dossier/{analysis_id}"


@router.post(f"{_BASE}/elements/{{element_id}}/lock", response_model=LockOut)
async def acquire_element_lock(
    dossier_id: uuid.UUID,
    analysis_id: uuid.UUID,
    element_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
):
    """Prend (ou renouvelle) le verrou de l'élément avant de le modifier. Expire seul
    s'il n'est pas renouvelé. 409 si un autre instructeur le détient : le message dit
    qui, et jusqu'à quand."""
    analyses = DossierAnalysisRepository(db)
    _ensure_editable(await _analysis_or_404(analyses, dossier_id, analysis_id))
    collaboration = AnalysisCollaborationRepository(db)
    if await collaboration.get_element(analysis_id, element_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Élément introuvable")
    element = await collaboration.acquire_lock(analysis_id, element_id, user_id=user.user_id, name=display_name(user))
    if element is None:
        holder = await collaboration.get_element(analysis_id, element_id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ElementLockedError(holder.locked_by_name, holder.locked_by or "", holder.locked_until).message,
        )
    return lock_out(element, user.user_id)


@router.delete(f"{_BASE}/elements/{{element_id}}/lock", status_code=status.HTTP_204_NO_CONTENT)
async def release_element_lock(
    dossier_id: uuid.UUID,
    analysis_id: uuid.UUID,
    element_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
):
    """Libère le verrou de l'utilisateur (sans effet s'il n'en a pas). 409 si un autre
    instructeur en détient un valide."""
    await _analysis_or_404(DossierAnalysisRepository(db), dossier_id, analysis_id)
    released = await AnalysisCollaborationRepository(db).release_lock(analysis_id, element_id, user_id=user.user_id)
    if not released:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ce verrou appartient à un autre instructeur")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put(f"{_BASE}/presence", status_code=status.HTTP_204_NO_CONTENT)
async def heartbeat_presence(
    dossier_id: uuid.UUID,
    analysis_id: uuid.UUID,
    body: PresenceIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
):
    """Battement de cœur : sur quel élément je suis, et si je le consulte ou l'édite.
    À renvoyer régulièrement (la présence expire seule)."""
    await _analysis_or_404(DossierAnalysisRepository(db), dossier_id, analysis_id)
    collaboration = AnalysisCollaborationRepository(db)
    element_id = body.element_id
    if element_id is not None and await collaboration.get_element(analysis_id, element_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Élément introuvable")
    await collaboration.upsert_presence(
        analysis_id, user_id=user.user_id, name=display_name(user), element_id=element_id, mode=body.mode
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(f"{_BASE}/presence", status_code=status.HTTP_204_NO_CONTENT)
async def leave_presence(
    dossier_id: uuid.UUID,
    analysis_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
):
    await _analysis_or_404(DossierAnalysisRepository(db), dossier_id, analysis_id)
    await AnalysisCollaborationRepository(db).remove_presence(analysis_id, user_id=user.user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(f"{_BASE}/presence", response_model=LiveSnapshot)
async def get_presence(
    dossier_id: uuid.UUID,
    analysis_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
):
    """Qui est où, et quels éléments sont verrouillés (instantané)."""
    await _analysis_or_404(DossierAnalysisRepository(db), dossier_id, analysis_id)
    return await AnalysisCollaborationRepository(db).snapshot(analysis_id, current_user_id=user.user_id)


async def _live_events(request: Request, analysis_id: uuid.UUID, user_id: str) -> AsyncIterator[str]:
    """Émet l'instantané à l'ouverture puis à chaque changement (lecture régulière de
    la base, comme les autres flux SSE). Un commentaire de maintien toutes les ~15 s
    garde la connexion ouverte à travers les proxys. S'arrête à la déconnexion."""
    last_payload: str | None = None
    idle = 0.0
    while not await request.is_disconnected():
        async with async_session_factory() as session:
            snapshot = await AnalysisCollaborationRepository(session).snapshot(analysis_id, current_user_id=user_id)
        payload = json.dumps(snapshot.model_dump(mode="json"), sort_keys=True)
        if payload != last_payload:
            last_payload = payload
            idle = 0.0
            yield f"event: live\ndata: {payload}\n\n"
        elif idle >= 15:
            idle = 0.0
            yield ": keepalive\n\n"
        await asyncio.sleep(settings.LIVE_POLL_SECONDS)
        idle += settings.LIVE_POLL_SECONDS


@router.get(f"{_BASE}/live")
async def stream_live(
    request: Request,
    dossier_id: uuid.UUID,
    analysis_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
):
    """Flux SSE temps réel : présence des instructeurs et verrous des éléments."""
    await _analysis_or_404(DossierAnalysisRepository(db), dossier_id, analysis_id)
    return StreamingResponse(
        _live_events(request, analysis_id, user.user_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
