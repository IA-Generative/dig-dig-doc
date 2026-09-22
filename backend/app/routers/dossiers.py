import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.factory import get_current_user
from app.db import get_db
from app.models.dossier import Dossier
from app.repositories.analyse_repository import AnalyseRepository
from app.repositories.dossier_repository import DossierRepository
from app.schemas.dossier import DossierCreate, DossierOut

router = APIRouter(prefix="/dossiers", tags=["Dossiers"], dependencies=[Depends(get_current_user)])


async def _get_or_404(repository: DossierRepository, dossier_id: uuid.UUID) -> Dossier:
    dossier = await repository.get(dossier_id)
    if dossier is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dossier introuvable")
    return dossier


@router.get("", response_model=list[DossierOut])
async def list_dossiers(db: Annotated[AsyncSession, Depends(get_db)]) -> list[Dossier]:
    return await DossierRepository(db).list_all()


@router.post("", response_model=DossierOut, status_code=status.HTTP_201_CREATED)
async def create_dossier(body: DossierCreate, db: Annotated[AsyncSession, Depends(get_db)]) -> Dossier:
    analyse_repository = AnalyseRepository(db)
    analyse = await analyse_repository.get(body.analyse_id)
    if analyse is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Analyse introuvable")

    dossier_repository = DossierRepository(db)
    dossier = await dossier_repository.create(name=body.name, analyse=analyse)
    return await _get_or_404(dossier_repository, dossier.id)


@router.get("/{dossier_id}", response_model=DossierOut)
async def get_dossier(dossier_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]) -> Dossier:
    return await _get_or_404(DossierRepository(db), dossier_id)


@router.post("/{dossier_id}/documents", response_model=DossierOut)
async def add_documents(
    dossier_id: uuid.UUID, files: list[UploadFile], db: Annotated[AsyncSession, Depends(get_db)]
) -> Dossier:
    repository = DossierRepository(db)
    dossier = await _get_or_404(repository, dossier_id)
    documents = [{"name": f.filename or "document", "size": f.size or 0} for f in files]
    await repository.add_documents(dossier, documents)
    return dossier


@router.post("/{dossier_id}/launch", response_model=DossierOut)
async def launch_dossier(dossier_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]) -> Dossier:
    dossier_repository = DossierRepository(db)
    dossier = await _get_or_404(dossier_repository, dossier_id)
    analyse = await AnalyseRepository(db).get(dossier.analyse_id)
    if analyse is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Analyse introuvable")
    await dossier_repository.launch(dossier, analyse)
    return dossier


@router.post("/{dossier_id}/stop", response_model=DossierOut)
async def stop_dossier(dossier_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]) -> Dossier:
    repository = DossierRepository(db)
    dossier = await _get_or_404(repository, dossier_id)
    await repository.stop(dossier)
    return dossier
