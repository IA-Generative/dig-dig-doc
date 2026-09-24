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
from app.models.dossier_ephemere import DossierEphemere
from app.repositories.analyse_repository import AnalyseRepository
from app.repositories.dossier_repository import DossierRepository
from app.repositories.ephemeral_repository import EphemeralRepository
from app.schemas.dossier import DossierOut
from app.schemas.ephemeral import (
    EphemeralAnalyseCreate,
    EphemeralAnalyseCreated,
    EphemeralAnalyseOut,
    EphemeralRunCreated,
    EphemeralRunOut,
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


@router.post(
    "/analyses",
    response_model=EphemeralAnalyseCreated,
    status_code=status.HTTP_201_CREATED,
    summary="Crée une analyse éphémère complète en un seul appel",
    description="Crée une analyse (classification, extraction, agents) en une seule requête, contrairement au "
    "flux standard de la plateforme (POST /api/analyses puis un appel par champ à configurer). "
    "`persist=false` (défaut) : purgée automatiquement une fois son TTL écoulé, calculé à la fin du "
    "dernier run l'ayant utilisée (jamais à la création) - voir docs/ephemeral-api.md. `persist=true` : "
    "conservée indéfiniment, comme une Analyse classique. L'id renvoyé est toujours celui d'une "
    "`Analyse` normale de la plateforme (une ligne `analyse_ephemere` y est simplement associée).",
)
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


@router.get(
    "/analyses/{analyse_id}",
    response_model=EphemeralAnalyseOut,
    summary="Consulte une analyse éphémère",
    description="Scope strict : ne renvoie que les analyses créées via POST /api/ephemeral/analyses, et "
    "seulement à leur créateur (404 dans les deux autres cas - jamais 403, pour ne pas laisser deviner "
    "qu'un id existe mais appartient à quelqu'un d'autre). Une Analyse classique de la plateforme, même "
    "avec un id valide, tombe dans le même 404.",
    responses={404: {"description": "Analyse introuvable, pas éphémère, ou appartenant à un autre créateur."}},
)
async def get_ephemeral_analyse(
    analyse_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    identity: Annotated[EphemeralIdentity, Depends(get_ephemeral_identity)],
) -> EphemeralAnalyseOut:
    ephemeral_repository = EphemeralRepository(db)
    record = await _get_analyse_ephemere_or_404(ephemeral_repository, analyse_id, identity)

    analyse_repository = AnalyseRepository(db)
    analyse = await analyse_repository.get(analyse_id)
    if analyse is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analyse éphémère introuvable")
    return EphemeralAnalyseOut(
        **analyse_repository.to_schema(analyse).model_dump(),
        persist=record.persist,
        expires_at=record.expires_at,
    )


@router.delete(
    "/analyses/{analyse_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprime une analyse éphémère immédiatement",
    description="Suppression immédiate, sans attendre le TTL. Même scope strict que le GET (404 si pas "
    "éphémère ou pas créée par l'appelant). 409 si des runs (dossier_ephemere) référencent encore cette "
    "analyse - supprimez-les d'abord (DELETE /api/ephemeral/runs/{id}) : la contrainte est portée par la "
    "base (FK Dossier.analyse_id, ondelete=RESTRICT), pas une vérification applicative séparée.",
    responses={
        404: {"description": "Analyse introuvable, pas éphémère, ou appartenant à un autre créateur."},
        409: {"description": "Des dossiers référencent encore cette analyse."},
    },
)
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


async def _read_upload_files(files: list[UploadFile]) -> list[tuple[str, bytes, str]]:
    return [(f.filename or "document", await f.read(), f.content_type or "application/octet-stream") for f in files]


async def _create_run(
    *,
    db: AsyncSession,
    identity: EphemeralIdentity,
    analyse: Analyse,
    files: list[tuple[str, bytes, str]],
    persist: bool,
    ttl_hours: int,
) -> Dossier:
    """Cœur commun aux flux A et B (et au serveur MCP, cf. app/mcp/server.py) :
    upload + lancement immédiat du pipeline complet (pas d'étape `launch`
    séparée, contrairement à /api/dossiers), puis pose de la ligne
    dossier_ephemere. Réutilise telle quelle la logique d'upload/lancement
    de dossiers.py.

    `files` : (nom, contenu, type MIME) déjà lus en mémoire - pas de
    `UploadFile` FastAPI ici, pour rester appelable depuis un contexte qui
    n'en a pas (le serveur MCP décode du base64, pas un multipart HTTP)."""
    dossier_repository = DossierRepository(db)
    dossier = await dossier_repository.create(name=f"Run éphémère {uuid.uuid4()}", analyse=analyse)

    documents = []
    for name, data, mimetype in files:
        s3_key = f"dossiers/{dossier.id}/{uuid.uuid4()}-{name or 'document'}"
        await run_in_threadpool(s3_connector.upload, s3_key, data, mimetype)
        documents.append({"name": name or "document", "size": len(data), "s3_key": s3_key, "mimetype": mimetype})
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
    summary="Lance un run sur une analyse déjà créée (flux A)",
    description="Multipart : fichiers + persist (form, défaut false) + ttl_hours (query, défaut 24h, max "
    "17520h/2 ans, 400 si hors bornes). `analyse_id` peut être une analyse éphémère ou une `Analyse` "
    "classique de la plateforme (dans ce dernier cas, l'analyse n'est jamais modifiée). Le pipeline "
    "complet (classification, extraction, agents) démarre immédiatement, sans appel `launch` séparé.",
    responses={
        400: {"description": "ttl_hours hors bornes (doit être entre 1 et 17520)."},
        404: {"description": "analyse_id introuvable (ni éphémère, ni classique)."},
    },
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
        files=await _read_upload_files(files),
        persist=persist,
        ttl_hours=_validate_ttl_hours(ttl_hours),
    )
    return EphemeralRunCreated(run_id=dossier.id)


@router.post(
    "/runs",
    response_model=EphemeralRunCreated,
    status_code=status.HTTP_201_CREATED,
    summary="Crée l'analyse et lance le run en un seul appel (flux B)",
    description="Équivalent du flux A (POST .../analyses/{id}/runs) sans passer par la création préalable "
    "de l'analyse : `analyse_id` (form) référence une analyse déjà existante, éphémère ou classique. Mêmes "
    "règles de TTL/persist et même déclenchement immédiat du pipeline complet que le flux A.",
    responses={
        400: {"description": "ttl_hours hors bornes (doit être entre 1 et 17520)."},
        404: {"description": "analyse_id introuvable (ni éphémère, ni classique)."},
    },
)
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
        files=await _read_upload_files(files),
        persist=persist,
        ttl_hours=_validate_ttl_hours(ttl_hours),
    )
    return EphemeralRunCreated(run_id=dossier.id)


async def _get_owned_run_or_404(
    db: AsyncSession, run_id: uuid.UUID, identity: EphemeralIdentity
) -> tuple[Dossier, DossierEphemere]:
    """404, pas 403 (même rationale que _get_analyse_ephemere_or_404) : scope
    strict aux dossiers créés via ce routeur et à leur créateur."""
    record = await EphemeralRepository(db).get_dossier_ephemere(run_id)
    if record is None or record.created_by != identity.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run éphémère introuvable")
    dossier = await DossierRepository(db).get(run_id)
    if dossier is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run éphémère introuvable")
    return dossier, record


def _to_run_schema(dossier: Dossier, record: DossierEphemere) -> EphemeralRunOut:
    return EphemeralRunOut(
        **DossierOut.model_validate(dossier).model_dump(),
        persist=record.persist,
        ttl_hours=record.ttl_hours,
        expires_at=record.expires_at,
    )


@router.get(
    "/runs/{run_id}",
    response_model=EphemeralRunOut,
    summary="Consulte un run éphémère (statut + résultats)",
    description="Statut en cours, puis résultats complets (classification, entités, sorties des agents) une "
    "fois terminé. Scope strict : ne renvoie que les runs créés via ce routeur, et seulement à leur "
    "créateur (404 dans les deux autres cas).",
    responses={404: {"description": "Run introuvable, pas éphémère, ou appartenant à un autre créateur."}},
)
async def get_ephemeral_run(
    run_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    identity: Annotated[EphemeralIdentity, Depends(get_ephemeral_identity)],
) -> EphemeralRunOut:
    dossier, record = await _get_owned_run_or_404(db, run_id, identity)
    return _to_run_schema(dossier, record)


@router.post(
    "/runs/{run_id}/stop",
    response_model=EphemeralRunOut,
    summary="Arrête un run en cours",
    description="No-op si le run est déjà dans un état terminal (terminé/arrêté/échec) - même comportement "
    "que POST /api/dossiers/{id}/stop. Pose expires_at (voir docs/ephemeral-api.md) si ce n'est pas déjà "
    "fait. N'efface rien : le run reste consultable via GET, et sera purgé normalement au TTL, ou "
    "supprimable immédiatement via DELETE.",
    responses={404: {"description": "Run introuvable, pas éphémère, ou appartenant à un autre créateur."}},
)
async def stop_ephemeral_run(
    run_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    identity: Annotated[EphemeralIdentity, Depends(get_ephemeral_identity)],
) -> EphemeralRunOut:
    dossier, _ = await _get_owned_run_or_404(db, run_id, identity)
    dossier_repository = DossierRepository(db)
    ephemeral_repository = EphemeralRepository(db)
    # No-op si déjà dans un état terminal (terminé/arrêté/échec) - même
    # comportement que POST /api/dossiers/{id}/stop.
    await dossier_repository.stop(dossier)
    dossier = await dossier_repository.get(run_id)
    # mark_dossier_terminal est idempotent (no-op si déjà posé) : appelé
    # systématiquement plutôt que seulement quand stop() vient d'agir, pour
    # rattraper un éventuel dossier déjà arrêté/terminé sans expires_at.
    await ephemeral_repository.mark_dossier_terminal(dossier)
    record = await ephemeral_repository.get_dossier_ephemere(run_id)
    return _to_run_schema(dossier, record)


@router.delete(
    "/runs/{run_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Arrête (si besoin) et supprime un run immédiatement",
    description="Si le run est encore en_cours, l'arrête d'abord (même effet que POST .../stop), puis "
    "supprime immédiatement le dossier (documents, étapes d'exécution, résultats, fichiers S3), sans "
    "attendre expires_at. Ne touche pas à l'analyse liée (analyse_ephemere conservée). Même scope strict "
    "que le GET.",
    responses={404: {"description": "Run introuvable, pas éphémère, ou appartenant à un autre créateur."}},
)
async def delete_ephemeral_run(
    run_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    identity: Annotated[EphemeralIdentity, Depends(get_ephemeral_identity)],
) -> None:
    dossier, _ = await _get_owned_run_or_404(db, run_id, identity)
    dossier_repository = DossierRepository(db)
    if dossier.status == DossierStatus.EN_COURS:
        await dossier_repository.stop(dossier)
        dossier = await dossier_repository.get(run_id)
    # delete_dossier refuse encore en_attente/en_cours : un run éphémère est
    # toujours lancé immédiatement à la création (_create_run), en_attente
    # ne devrait jamais se produire en pratique - pas de branche dédiée.
    await dossier_repository.delete_dossier(dossier)
