"""Routes des propositions de modification de l'analyse de dossier (issue #114).

Une proposition n'applique rien : l'utilisateur l'accepte, la modifie ou la
rejette, et chaque décision est journalisée. Interne : jamais exposé côté
usager (#96)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.factory import RequestContext, get_current_user
from app.db import get_db
from app.models.analysis_proposal import ProposalStatus
from app.repositories.analysis_proposal_repository import (
    AnalysisProposalRepository,
    ProposalAlreadyDecidedError,
    ProposalTargetError,
    StaleProposalError,
)
from app.repositories.dossier_analysis_repository import DossierAnalysisRepository
from app.routers.dossier_analyses import _analysis_or_404, _dossier_or_404, _ensure_editable
from app.schemas.analysis_proposal import (
    ProposalCreateIn,
    ProposalDetailOut,
    ProposalEventOut,
    ProposalModifyIn,
    ProposalOut,
    ProposalRejectIn,
)
from app.schemas.dossier_analysis import InvalidElementValueError

router = APIRouter(prefix="/dossiers", tags=["Propositions"], dependencies=[Depends(get_current_user)])

_BASE = "/{dossier_id}/analyses-dossier/{analysis_id}/proposals"


def _repositories(db: AsyncSession) -> tuple[DossierAnalysisRepository, AnalysisProposalRepository]:
    analyses = DossierAnalysisRepository(db)
    return analyses, AnalysisProposalRepository(analyses)


@router.get("/{dossier_id}/analyse-dossier/proposals", response_model=list[ProposalOut])
async def list_current_proposals(
    dossier_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    proposal_status: Annotated[ProposalStatus | None, Query(alias="status")] = ProposalStatus.PENDING,
):
    """Propositions de l'analyse courante du dossier (en attente par défaut)."""
    await _dossier_or_404(db, dossier_id)
    analyses, proposals = _repositories(db)
    analysis = await analyses.get_current(dossier_id)
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aucune analyse pour ce dossier")
    return await proposals.list_proposals(analysis.id, proposal_status)


@router.get(_BASE, response_model=list[ProposalOut])
async def list_proposals(
    dossier_id: uuid.UUID,
    analysis_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    proposal_status: Annotated[ProposalStatus | None, Query(alias="status")] = None,
):
    analyses, proposals = _repositories(db)
    await _analysis_or_404(analyses, dossier_id, analysis_id)
    return await proposals.list_proposals(analysis_id, proposal_status)


@router.post(_BASE, response_model=ProposalOut, status_code=status.HTTP_201_CREATED)
async def create_proposal(
    dossier_id: uuid.UUID,
    analysis_id: uuid.UUID,
    body: ProposalCreateIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
):
    """Propose de modifier un élément (ou d'en créer un). N'applique rien."""
    analyses, proposals = _repositories(db)
    analysis = await _analysis_or_404(analyses, dossier_id, analysis_id)
    _ensure_editable(analysis)
    try:
        return await proposals.create(
            analysis,
            proposed_by=user.user_id,
            value=body.value,
            reason=body.reason,
            element_id=body.element_id,
            kind=body.kind,
            definition_name=body.definition_name,
            source_type=body.source_type,
            source_id=body.source_id,
            model=body.model,
            prompt_version=body.prompt_version,
        )
    except ProposalTargetError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except InvalidElementValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error


@router.get(f"{_BASE}/{{proposal_id}}", response_model=ProposalDetailOut)
async def get_proposal(
    dossier_id: uuid.UUID, analysis_id: uuid.UUID, proposal_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]
):
    """Une proposition et son journal (proposée, décision, durée...)."""
    analyses, proposals = _repositories(db)
    await _analysis_or_404(analyses, dossier_id, analysis_id)
    proposal = await proposals.get(analysis_id, proposal_id)
    if proposal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposition introuvable")
    events = await proposals.list_events(proposal_id)
    return ProposalDetailOut(
        **ProposalOut.model_validate(proposal).model_dump(),
        events=[ProposalEventOut.model_validate(e) for e in events],
    )


async def _decide(db: AsyncSession, dossier_id: uuid.UUID, analysis_id: uuid.UUID, action):
    analyses, proposals = _repositories(db)
    analysis = await _analysis_or_404(analyses, dossier_id, analysis_id)
    _ensure_editable(analysis)
    try:
        return await action(proposals, analysis)
    except ProposalTargetError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ProposalAlreadyDecidedError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Cette proposition a déjà été traitée"
        ) from error
    except StaleProposalError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="L'élément a été modifié depuis cette proposition : rejetez-la ou refaites-la",
        ) from error
    except InvalidElementValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error


@router.post(f"{_BASE}/{{proposal_id}}/accept", response_model=ProposalOut)
async def accept_proposal(
    dossier_id: uuid.UUID,
    analysis_id: uuid.UUID,
    proposal_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
):
    """Accepte la proposition telle quelle : crée une version de l'élément."""
    return await _decide(
        db,
        dossier_id,
        analysis_id,
        lambda proposals, analysis: proposals.accept(analysis, proposal_id, user_id=user.user_id),
    )


@router.post(f"{_BASE}/{{proposal_id}}/modify", response_model=ProposalOut)
async def modify_proposal(
    dossier_id: uuid.UUID,
    analysis_id: uuid.UUID,
    proposal_id: uuid.UUID,
    body: ProposalModifyIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
):
    """Accepte avec une autre valeur que celle proposée."""
    return await _decide(
        db,
        dossier_id,
        analysis_id,
        lambda proposals, analysis: proposals.modify(
            analysis, proposal_id, user_id=user.user_id, value=body.value, note=body.reason
        ),
    )


@router.post(f"{_BASE}/{{proposal_id}}/reject", response_model=ProposalOut)
async def reject_proposal(
    dossier_id: uuid.UUID,
    analysis_id: uuid.UUID,
    proposal_id: uuid.UUID,
    body: ProposalRejectIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
):
    """Rejette la proposition : rien n'est appliqué."""
    return await _decide(
        db,
        dossier_id,
        analysis_id,
        lambda proposals, analysis: proposals.reject(analysis, proposal_id, user_id=user.user_id, note=body.reason),
    )
