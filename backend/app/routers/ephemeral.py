import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.ephemeral import EphemeralIdentity, get_ephemeral_identity
from app.db import get_db
from app.models.analyse import AgentTool, EntityDefinition, LabelDefinition
from app.models.analyse_ephemere import AnalyseEphemere
from app.repositories.analyse_repository import AnalyseRepository
from app.repositories.ephemeral_repository import EphemeralRepository
from app.schemas.analyse import AnalyseOut
from app.schemas.ephemeral import EphemeralAnalyseCreate, EphemeralAnalyseCreated

router = APIRouter(prefix="/ephemeral", tags=["Ephemeral"], dependencies=[Depends(get_ephemeral_identity)])


async def _get_analyse_ephemere_or_404(
    repository: EphemeralRepository, analyse_id: uuid.UUID, identity: EphemeralIdentity
) -> AnalyseEphemere:
    """404, pas 403 : ne pas laisser deviner qu'un id existe mais appartient
    à quelqu'un d'autre. Scope strict aux analyses créées via ce routeur
    (cf. docs/ephemeral-api.md) - une Analyse classique de la plateforme n'a
    pas de ligne AnalyseEphemere et tombe dans le même 404."""
    record = await repository.get_analyse_ephemere(analyse_id)
    if record is None or record.created_by != identity.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analyse éphémère introuvable")
    return record


@router.post("/analyses", response_model=EphemeralAnalyseCreated, status_code=status.HTTP_201_CREATED)
async def create_ephemeral_analyse(
    body: EphemeralAnalyseCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    identity: Annotated[EphemeralIdentity, Depends(get_ephemeral_identity)],
) -> EphemeralAnalyseCreated:
    analyse_repository = AnalyseRepository(db)
    analyse = await analyse_repository.create(name=body.name, description=body.description)
    # create() ne recharge pas les relations (labels/entities/agents) après
    # commit : sans ce re-fetch (via _base_query, eager load), les accéder
    # dans les update_* ci-dessous ferait un lazy-load hors contexte async.
    analyse = await analyse_repository.get(analyse.id)

    if body.classification_prompt:
        await analyse_repository.update_classification_prompt(analyse, body.classification_prompt)
    if body.labels:
        await analyse_repository.update_classification_labels(
            analyse, [LabelDefinition(name=lbl.name, definition=lbl.definition) for lbl in body.labels]
        )
    if body.extraction_prompt:
        await analyse_repository.update_extraction_prompt(analyse, body.extraction_prompt)
    if body.entities:
        await analyse_repository.update_extraction_entities(
            analyse,
            [EntityDefinition(name=ent.name, definition=ent.definition, type=ent.type) for ent in body.entities],
        )
    for agent in body.agents:
        await analyse_repository.add_agent(
            analyse,
            name=agent.name,
            prompt=agent.prompt,
            tools=[AgentTool(t) for t in agent.tools],
            output=agent.output,
            model=agent.model,
        )

    await EphemeralRepository(db).create_analyse_ephemere(
        analyse_id=analyse.id, persist=body.persist, created_by=identity.id
    )
    return EphemeralAnalyseCreated(analyse_id=analyse.id)


@router.get("/analyses/{analyse_id}", response_model=AnalyseOut)
async def get_ephemeral_analyse(
    analyse_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    identity: Annotated[EphemeralIdentity, Depends(get_ephemeral_identity)],
) -> AnalyseOut:
    ephemeral_repository = EphemeralRepository(db)
    await _get_analyse_ephemere_or_404(ephemeral_repository, analyse_id, identity)

    analyse_repository = AnalyseRepository(db)
    analyse = await analyse_repository.get(analyse_id)
    if analyse is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analyse éphémère introuvable")
    return analyse_repository.to_schema(analyse)


@router.delete("/analyses/{analyse_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ephemeral_analyse(
    analyse_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    identity: Annotated[EphemeralIdentity, Depends(get_ephemeral_identity)],
) -> None:
    ephemeral_repository = EphemeralRepository(db)
    await _get_analyse_ephemere_or_404(ephemeral_repository, analyse_id, identity)

    analyse_repository = AnalyseRepository(db)
    analyse = await analyse_repository.get(analyse_id)
    if analyse is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analyse éphémère introuvable")
    try:
        # La ligne AnalyseEphemere cascade avec l'Analyse (ondelete="CASCADE"),
        # pas besoin de la supprimer séparément.
        await analyse_repository.delete(analyse)
    except IntegrityError as error:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Des dossiers référencent encore cette analyse - supprimez-les d'abord",
        ) from error
