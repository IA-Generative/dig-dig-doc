import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Query, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.celery_client import (
    dispatch_agent_execution,
    dispatch_classification,
    dispatch_entity_extraction,
    dispatch_text_extraction,
)
from app.connectors import s3_connector
from app.core.security.ephemeral import EphemeralIdentity, get_ephemeral_identity
from app.db import get_db
from app.models.analyse import AgentTool, Analyse, EntityDefinition, LabelDefinition
from app.models.analyse_ephemere import AnalyseEphemere
from app.models.dossier import Dossier, DossierStatus
from app.repositories.analyse_repository import AnalyseRepository
from app.repositories.dossier_repository import DossierRepository
from app.repositories.ephemeral_repository import EphemeralRepository
from app.schemas.analyse import AnalyseOut
from app.schemas.dossier import DossierOut
from app.schemas.ephemeral import (
    EphemeralAnalyseCreate,
    EphemeralAnalyseCreated,
    EphemeralRunCreated,
)

router = APIRouter(prefix="/ephemeral", tags=["Ephemeral"], dependencies=[Depends(get_ephemeral_identity)])

# Cf. docs/ephemeral-api.md, section "Principe du TTL".
TTL_DEFAULT_HOURS = 24
TTL_MAX_HOURS = 17520  # 2 ans


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


def _validate_ttl_hours(ttl_hours: int | None) -> int:
    value = TTL_DEFAULT_HOURS if ttl_hours is None else ttl_hours
    if value <= 0 or value > TTL_MAX_HOURS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"ttl_hours doit être compris entre 1 et {TTL_MAX_HOURS} (2 ans)",
        )
    return value


async def _create_run(
    *,
    db: AsyncSession,
    identity: EphemeralIdentity,
    analyse: Analyse,
    files: list[UploadFile],
    persist: bool,
    ttl_hours: int,
) -> Dossier:
    """Cœur commun aux flux A et B : upload + lancement immédiat du pipeline
    complet (pas d'étape `launch` séparée, contrairement à /api/dossiers),
    puis pose de la ligne dossier_ephemere. Réutilise telle quelle la
    logique d'upload/lancement de dossiers.py."""
    dossier_repository = DossierRepository(db)
    dossier = await dossier_repository.create(name=f"Run éphémère {uuid.uuid4()}", analyse=analyse)

    documents = []
    for f in files:
        data = await f.read()
        s3_key = f"dossiers/{dossier.id}/{uuid.uuid4()}-{f.filename or 'document'}"
        mimetype = f.content_type or "application/octet-stream"
        await run_in_threadpool(s3_connector.upload, s3_key, data, mimetype)
        documents.append({"name": f.filename or "document", "size": len(data), "s3_key": s3_key, "mimetype": mimetype})
    created = await dossier_repository.add_documents(dossier, documents)
    for document in created:
        dispatch_text_extraction(str(document.id))
    # add_documents() finit par un refresh(dossier) qui périme execution_steps
    # (accédée par launch() juste après) - même raison que le commentaire
    # équivalent dans dossiers.py:add_documents, un re-fetch recharge tout
    # via _base_query (populate_existing=True).
    dossier = await dossier_repository.get(dossier.id)

    await dossier_repository.launch(dossier, analyse)
    dispatch_classification(str(dossier.id))
    dispatch_entity_extraction(str(dossier.id))
    dispatch_agent_execution(str(dossier.id))

    ephemeral_repository = EphemeralRepository(db)
    analyse_ephemere = await ephemeral_repository.get_analyse_ephemere(analyse.id)
    await ephemeral_repository.create_dossier_ephemere(
        dossier_id=dossier.id,
        analyse_ephemere_id=analyse_ephemere.analyse_id if analyse_ephemere else None,
        persist=persist,
        ttl_hours=ttl_hours,
        created_by=identity.id,
    )
    # Pas `return dossier` : add_documents()/launch() réexpirent les
    # relations déjà chargées (même raison que le commentaire équivalent
    # dans dossiers.py:add_documents) - un re-fetch a le eager loading
    # complet de DossierRepository._base_query.
    return await dossier_repository.get(dossier.id)


@router.post(
    "/analyses/{analyse_id}/runs",
    response_model=EphemeralRunCreated,
    status_code=status.HTTP_201_CREATED,
)
async def create_ephemeral_run_for_analyse(
    analyse_id: uuid.UUID,
    files: list[UploadFile],
    db: Annotated[AsyncSession, Depends(get_db)],
    identity: Annotated[EphemeralIdentity, Depends(get_ephemeral_identity)],
    persist: Annotated[bool, Form()] = False,
    ttl_hours: Annotated[int | None, Query()] = None,
) -> EphemeralRunCreated:
    analyse = await AnalyseRepository(db).get(analyse_id)
    if analyse is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analyse introuvable")
    dossier = await _create_run(
        db=db,
        identity=identity,
        analyse=analyse,
        files=files,
        persist=persist,
        ttl_hours=_validate_ttl_hours(ttl_hours),
    )
    return EphemeralRunCreated(run_id=dossier.id)


@router.post("/runs", response_model=EphemeralRunCreated, status_code=status.HTTP_201_CREATED)
async def create_ephemeral_run(
    files: list[UploadFile],
    db: Annotated[AsyncSession, Depends(get_db)],
    identity: Annotated[EphemeralIdentity, Depends(get_ephemeral_identity)],
    analyse_id: Annotated[uuid.UUID, Form()],
    persist: Annotated[bool, Form()] = False,
    ttl_hours: Annotated[int | None, Query()] = None,
) -> EphemeralRunCreated:
    analyse = await AnalyseRepository(db).get(analyse_id)
    if analyse is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analyse introuvable")
    dossier = await _create_run(
        db=db,
        identity=identity,
        analyse=analyse,
        files=files,
        persist=persist,
        ttl_hours=_validate_ttl_hours(ttl_hours),
    )
    return EphemeralRunCreated(run_id=dossier.id)


async def _get_owned_run_or_404(db: AsyncSession, run_id: uuid.UUID, identity: EphemeralIdentity) -> Dossier:
    """404, pas 403 (même rationale que _get_analyse_ephemere_or_404) : scope
    strict aux dossiers créés via ce routeur et à leur créateur."""
    record = await EphemeralRepository(db).get_dossier_ephemere(run_id)
    if record is None or record.created_by != identity.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run éphémère introuvable")
    dossier = await DossierRepository(db).get(run_id)
    if dossier is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run éphémère introuvable")
    return dossier


@router.get("/runs/{run_id}", response_model=DossierOut)
async def get_ephemeral_run(
    run_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    identity: Annotated[EphemeralIdentity, Depends(get_ephemeral_identity)],
) -> Dossier:
    return await _get_owned_run_or_404(db, run_id, identity)


@router.post("/runs/{run_id}/stop", response_model=DossierOut)
async def stop_ephemeral_run(
    run_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    identity: Annotated[EphemeralIdentity, Depends(get_ephemeral_identity)],
) -> Dossier:
    dossier = await _get_owned_run_or_404(db, run_id, identity)
    dossier_repository = DossierRepository(db)
    # No-op si déjà dans un état terminal (terminé/arrêté/échec) - même
    # comportement que POST /api/dossiers/{id}/stop.
    await dossier_repository.stop(dossier)
    return await dossier_repository.get(run_id)


@router.delete("/runs/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ephemeral_run(
    run_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    identity: Annotated[EphemeralIdentity, Depends(get_ephemeral_identity)],
) -> None:
    dossier = await _get_owned_run_or_404(db, run_id, identity)
    dossier_repository = DossierRepository(db)
    if dossier.status == DossierStatus.EN_COURS:
        await dossier_repository.stop(dossier)
        dossier = await dossier_repository.get(run_id)
    # delete_dossier refuse encore en_attente/en_cours : un run éphémère est
    # toujours lancé immédiatement à la création (_create_run), en_attente
    # ne devrait jamais se produire en pratique - pas de branche dédiée.
    await dossier_repository.delete_dossier(dossier)
