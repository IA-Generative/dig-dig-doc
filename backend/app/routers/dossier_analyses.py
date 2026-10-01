"""Routes de l'analyse de dossier (issue #112, parent #106).

Lecture, restauration d'une version et révisions. Interne : réservé aux
utilisateurs authentifiés, jamais exposé côté usager (#96). La création des
analyses et de leurs éléments est faite par la génération (#113) et les
propositions (#114), pas par ces routes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.factory import RequestContext, get_current_user
from app.db import get_db
from app.models.dossier_analysis import DossierAnalysis, DossierAnalysisStatus, ElementVersionOrigin
from app.repositories.dossier_analysis_repository import DossierAnalysisRepository
from app.repositories.dossier_repository import DossierRepository
from app.schemas.dossier_analysis import (
    AnalysisElementOut,
    AnalysisRevisionOut,
    AnalysisRevisionSummaryOut,
    AnalysisUnitOut,
    DossierAnalysisOut,
    DossierAnalysisSummaryOut,
    ElementCreateIn,
    ElementVersionCreateIn,
    ElementVersionOut,
    InvalidElementValueError,
    RestoreVersionIn,
    RevisionIn,
    RevisionItemOut,
)

router = APIRouter(prefix="/dossiers", tags=["Analyse de dossier"], dependencies=[Depends(get_current_user)])


async def _dossier_or_404(db: AsyncSession, dossier_id: uuid.UUID) -> None:
    if await DossierRepository(db).get(dossier_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dossier introuvable")


async def _analysis_or_404(
    repository: DossierAnalysisRepository, dossier_id: uuid.UUID, analysis_id: uuid.UUID
) -> DossierAnalysis:
    analysis = await repository.get(dossier_id, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analyse de dossier introuvable")
    return analysis


def _ensure_editable(analysis: DossierAnalysis) -> None:
    """Une analyse figée ne reçoit plus aucune modification."""
    if analysis.status == DossierAnalysisStatus.FIGEE:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cette analyse est figée")


@router.get("/{dossier_id}/analyses-dossier", response_model=list[DossierAnalysisSummaryOut])
async def list_dossier_analyses(dossier_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]):
    """Les analyses du dossier (une par exécution), la plus récente d'abord."""
    await _dossier_or_404(db, dossier_id)
    return await DossierAnalysisRepository(db).list_analyses(dossier_id)


@router.get("/{dossier_id}/analyse-dossier", response_model=DossierAnalysisOut)
async def get_current_dossier_analysis(dossier_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]):
    """L'analyse courante du dossier (la plus récente) avec ses éléments."""
    await _dossier_or_404(db, dossier_id)
    repository = DossierAnalysisRepository(db)
    analysis = await repository.get_current(dossier_id)
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aucune analyse pour ce dossier")
    return await repository.build_out(analysis)


@router.get("/{dossier_id}/analyses-dossier/{analysis_id}", response_model=DossierAnalysisOut)
async def get_dossier_analysis(
    dossier_id: uuid.UUID, analysis_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]
):
    repository = DossierAnalysisRepository(db)
    return await repository.build_out(await _analysis_or_404(repository, dossier_id, analysis_id))


@router.get("/{dossier_id}/analyses-dossier/{analysis_id}/units", response_model=list[AnalysisUnitOut])
async def list_analysis_units(
    dossier_id: uuid.UUID, analysis_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]
):
    repository = DossierAnalysisRepository(db)
    await _analysis_or_404(repository, dossier_id, analysis_id)
    return await repository.list_units(analysis_id)


@router.get(
    "/{dossier_id}/analyses-dossier/{analysis_id}/elements/{element_id}/versions",
    response_model=list[ElementVersionOut],
)
async def list_element_versions(
    dossier_id: uuid.UUID, analysis_id: uuid.UUID, element_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]
):
    """Historique complet d'un élément, de la plus ancienne à la plus récente."""
    repository = DossierAnalysisRepository(db)
    await _analysis_or_404(repository, dossier_id, analysis_id)
    if await repository.get_element(analysis_id, element_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Élément introuvable")
    return await repository.list_versions(element_id)


@router.post(
    "/{dossier_id}/analyses-dossier/{analysis_id}/elements/{element_id}/restore",
    response_model=ElementVersionOut,
    status_code=status.HTTP_201_CREATED,
)
async def restore_element_version(
    dossier_id: uuid.UUID,
    analysis_id: uuid.UUID,
    element_id: uuid.UUID,
    body: RestoreVersionIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
):
    """Restaure une version antérieure : ajoute une nouvelle version qui en
    reprend la valeur et devient la version retenue. Rien n'est supprimé."""
    repository = DossierAnalysisRepository(db)
    _ensure_editable(await _analysis_or_404(repository, dossier_id, analysis_id))
    element = await repository.get_element(analysis_id, element_id)
    if element is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Élément introuvable")
    versions = await repository.list_versions(element_id)
    version = next((v for v in versions if v.id == body.version_id), None)
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version introuvable pour cet élément")
    try:
        return await repository.restore_version(element, version, author_id=user.user_id, reason=body.reason)
    except InvalidElementValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error


@router.post(
    "/{dossier_id}/analyses-dossier/{analysis_id}/elements",
    response_model=AnalysisElementOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_element(
    dossier_id: uuid.UUID,
    analysis_id: uuid.UUID,
    body: ElementCreateIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
):
    """Ajoute à la main un élément (entité, classification, relation,
    synthèse ou champ) : sa première version est celle de l'instructeur."""
    repository = DossierAnalysisRepository(db)
    analysis = await _analysis_or_404(repository, dossier_id, analysis_id)
    _ensure_editable(analysis)
    try:
        element = await repository.create_element(
            analysis,
            kind=body.kind,
            value=body.value,
            origin=ElementVersionOrigin.INSTRUCTOR,
            definition_name=body.definition_name,
            author_id=user.user_id,
            reason=body.reason,
            source_type=body.source_type,
            source_id=body.source_id,
        )
    except InvalidElementValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    return await repository.element_out(element)


@router.post(
    "/{dossier_id}/analyses-dossier/{analysis_id}/elements/{element_id}/versions",
    response_model=ElementVersionOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_element_version(
    dossier_id: uuid.UUID,
    analysis_id: uuid.UUID,
    element_id: uuid.UUID,
    body: ElementVersionCreateIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
):
    """Apporte une nouvelle valeur à un élément, avec auteur et motif. Elle
    devient la version retenue ; la prédiction du modèle reste conservée."""
    repository = DossierAnalysisRepository(db)
    _ensure_editable(await _analysis_or_404(repository, dossier_id, analysis_id))
    element = await repository.get_element(analysis_id, element_id)
    if element is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Élément introuvable")
    try:
        return await repository.add_version(
            element,
            value=body.value,
            origin=ElementVersionOrigin.INSTRUCTOR,
            author_id=user.user_id,
            reason=body.reason,
            source_type=body.source_type,
            source_id=body.source_id,
        )
    except InvalidElementValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error


@router.get("/{dossier_id}/analyses-dossier/{analysis_id}/revisions", response_model=list[AnalysisRevisionSummaryOut])
async def list_revisions(dossier_id: uuid.UUID, analysis_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]):
    repository = DossierAnalysisRepository(db)
    await _analysis_or_404(repository, dossier_id, analysis_id)
    return await repository.list_revisions(analysis_id)


@router.post(
    "/{dossier_id}/analyses-dossier/{analysis_id}/revisions",
    response_model=AnalysisRevisionOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_revision(
    dossier_id: uuid.UUID,
    analysis_id: uuid.UUID,
    body: RevisionIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
):
    """Instantané de l'analyse : la version retenue de chaque élément."""
    repository = DossierAnalysisRepository(db)
    analysis = await _analysis_or_404(repository, dossier_id, analysis_id)
    revision, items = await repository.create_revision(analysis, author_id=user.user_id, label=body.label)
    return AnalysisRevisionOut(
        **AnalysisRevisionSummaryOut.model_validate(revision).model_dump(),
        items=[RevisionItemOut(element_id=i.element_id, version_id=i.version_id) for i in items],
    )


@router.get("/{dossier_id}/analyses-dossier/{analysis_id}/revisions/{revision_id}", response_model=AnalysisRevisionOut)
async def get_revision(
    dossier_id: uuid.UUID,
    analysis_id: uuid.UUID,
    revision_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    repository = DossierAnalysisRepository(db)
    await _analysis_or_404(repository, dossier_id, analysis_id)
    revision = await repository.get_revision(analysis_id, revision_id)
    if revision is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Révision introuvable")
    items = await repository.list_revision_items(revision_id)
    return AnalysisRevisionOut(
        **AnalysisRevisionSummaryOut.model_validate(revision).model_dump(),
        items=[RevisionItemOut(element_id=i.element_id, version_id=i.version_id) for i in items],
    )
