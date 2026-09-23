import asyncio
import json
import uuid
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.celery_client import dispatch_text_extraction
from app.connectors import s3_connector
from app.core.security.factory import RequestContext, get_current_user
from app.db import get_db
from app.models.conversation import MessageRole
from app.models.dossier import Dossier, DossierStatus, TextExtractionStatus
from app.repositories.analyse_repository import AnalyseRepository
from app.repositories.dossier_repository import DossierRepository
from app.schemas.dossier import (
    ConversationOut,
    DossierCreate,
    DossierDocumentLabelIn,
    DossierDocumentOut,
    DossierOut,
    MessageIn,
    PredictionValidationIn,
    PredictionValidationOut,
)
from app.schemas.pagination import Page

router = APIRouter(
    prefix="/dossiers", tags=["Dossiers"], dependencies=[Depends(get_current_user)]
)


async def _get_or_404(repository: DossierRepository, dossier_id: uuid.UUID) -> Dossier:
    dossier = await repository.get(dossier_id)
    if dossier is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dossier introuvable"
        )
    return dossier


@router.get("", response_model=Page[DossierOut])
async def list_dossiers(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Page[DossierOut]:
    dossiers, total = await DossierRepository(db).list_paginated(
        page=page, page_size=page_size
    )
    return Page.of(list(dossiers), total=total, page=page, page_size=page_size)


@router.post("", response_model=DossierOut, status_code=status.HTTP_201_CREATED)
async def create_dossier(
    body: DossierCreate, db: Annotated[AsyncSession, Depends(get_db)]
) -> Dossier:
    analyse_repository = AnalyseRepository(db)
    analyse = await analyse_repository.get(body.analyse_id)
    if analyse is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Analyse introuvable"
        )

    dossier_repository = DossierRepository(db)
    dossier = await dossier_repository.create(name=body.name, analyse=analyse)
    return await _get_or_404(dossier_repository, dossier.id)


@router.get("/{dossier_id}", response_model=DossierOut)
async def get_dossier(
    dossier_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]
) -> Dossier:
    return await _get_or_404(DossierRepository(db), dossier_id)


@router.post("/{dossier_id}/documents", response_model=DossierOut)
async def add_documents(
    dossier_id: uuid.UUID,
    files: list[UploadFile],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Dossier:
    repository = DossierRepository(db)
    dossier = await _get_or_404(repository, dossier_id)
    documents = []
    for f in files:
        data = await f.read()
        s3_key = f"dossiers/{dossier_id}/{uuid.uuid4()}-{f.filename or 'document'}"
        mimetype = f.content_type or "application/octet-stream"
        # boto3 est synchrone : hors du threadpool, cet appel bloquerait la
        # boucle asyncio le temps de l'upload.
        await run_in_threadpool(s3_connector.upload, s3_key, data, mimetype)
        documents.append(
            {
                "name": f.filename or "document",
                "size": len(data),
                "s3_key": s3_key,
                "mimetype": mimetype,
            }
        )
    created = await repository.add_documents(dossier, documents)
    for document in created:
        dispatch_text_extraction(str(document.id))
    # Pas `return dossier` : refresh(dossier) (dans add_documents) réexpire
    # `documents`, dont les nouveaux DossierDocument n'ont pas `pages` chargée
    # (MissingGreenlet à la sérialisation) - une requête fraîche via
    # _get_or_404 a le eager loading complet de _base_query.
    return await _get_or_404(repository, dossier_id)


@router.put(
    "/{dossier_id}/documents/{document_id}/label", response_model=DossierDocumentOut
)
async def set_document_label(
    dossier_id: uuid.UUID,
    document_id: uuid.UUID,
    body: DossierDocumentLabelIn,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    repository = DossierRepository(db)
    document = await repository.get_document(dossier_id, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document introuvable"
        )
    await repository.set_document_label(document, body.label)
    return document


@router.get("/{dossier_id}/documents/{document_id}/pages/{page_id}/screenshot")
async def get_page_screenshot(
    dossier_id: uuid.UUID,
    document_id: uuid.UUID,
    page_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Relaie la capture d'une page depuis S3 - jamais d'URL S3 signée
    renvoyée au frontend : seule cette route (protégée par la session
    Keycloak, comme tout /api/dossiers/*) a les identifiants du bucket."""
    repository = DossierRepository(db)
    document = await repository.get_document(dossier_id, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document introuvable"
        )
    page = await repository.get_page(document_id, page_id)
    if page is None or page.screenshot_key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Capture introuvable"
        )
    data, content_type = await run_in_threadpool(
        s3_connector.download, page.screenshot_key
    )
    return Response(content=data, media_type=content_type)


@router.post("/{dossier_id}/launch", response_model=DossierOut)
async def launch_dossier(
    dossier_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]
) -> Dossier:
    dossier_repository = DossierRepository(db)
    dossier = await _get_or_404(dossier_repository, dossier_id)
    analyse = await AnalyseRepository(db).get(dossier.analyse_id)
    if analyse is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Analyse introuvable"
        )
    await dossier_repository.launch(dossier, analyse)
    return dossier


@router.post("/{dossier_id}/stop", response_model=DossierOut)
async def stop_dossier(
    dossier_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]
) -> Dossier:
    repository = DossierRepository(db)
    dossier = await _get_or_404(repository, dossier_id)
    await repository.stop(dossier)
    return dossier


@router.get("/{dossier_id}/conversations", response_model=list[ConversationOut])
async def list_conversations(
    dossier_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
):
    repository = DossierRepository(db)
    await _get_or_404(repository, dossier_id)
    return await repository.list_conversations(dossier_id, user.user_id)


@router.post(
    "/{dossier_id}/conversations",
    response_model=ConversationOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    dossier_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
):
    repository = DossierRepository(db)
    await _get_or_404(repository, dossier_id)
    return await repository.create_conversation(dossier_id, user.user_id)


@router.post(
    "/{dossier_id}/conversations/{conversation_id}/messages",
    response_model=ConversationOut,
)
async def add_message(
    dossier_id: uuid.UUID,
    conversation_id: uuid.UUID,
    body: MessageIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
):
    repository = DossierRepository(db)
    await _get_or_404(repository, dossier_id)
    conversation = await repository.get_conversation(conversation_id)
    if (
        conversation is None
        or conversation.dossier_id != dossier_id
        or conversation.user_id != user.user_id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation introuvable"
        )
    return await repository.add_message(conversation, MessageRole.USER, body.content)


@router.put(
    "/{dossier_id}/documents/{document_id}/pages/{page_id}/predictions/{prediction_id}/validations",
    response_model=PredictionValidationOut,
)
async def validate_prediction(
    dossier_id: uuid.UUID,
    document_id: uuid.UUID,
    page_id: uuid.UUID,
    prediction_id: uuid.UUID,
    body: PredictionValidationIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
):
    repository = DossierRepository(db)
    document = await repository.get_document(dossier_id, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document introuvable"
        )
    page = await repository.get_page(document_id, page_id)
    prediction = (
        await repository.get_prediction(page_id, prediction_id) if page else None
    )
    if page is None or prediction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Prédiction introuvable"
        )
    updated = await repository.add_prediction_validation(
        prediction,
        validator_user_id=user.user_id,
        status=body.status,
        corrected_value=body.corrected_value,
        bounding_box=body.bounding_box.model_dump() if body.bounding_box else None,
    )
    return updated.validations[-1]


_TERMINAL_STATUSES = {DossierStatus.TERMINE, DossierStatus.ARRETE, DossierStatus.ECHEC}
_EXTRACTION_IN_PROGRESS = {
    TextExtractionStatus.EN_ATTENTE,
    TextExtractionStatus.EN_COURS,
}


def _has_active_work(dossier: Dossier) -> bool:
    """True tant qu'il y a du travail en cours : le dossier est lancé
    (classification/extraction/agents) ou au moins un document est en cours
    d'extraction de texte (qui démarre dès l'upload, avant tout lancement)."""
    if dossier.status == DossierStatus.EN_COURS:
        return True
    return any(
        doc.text_extraction_status in _EXTRACTION_IN_PROGRESS
        for doc in dossier.documents
    )


async def _execution_events(
    repository: DossierRepository, dossier_id: uuid.UUID
) -> AsyncIterator[str]:
    """Un événement SSE par changement d'état, jusqu'à ce qu'il n'y ait plus
    de travail actif (dossier terminal ou extraction de texte terminée) -
    pas de bus de messages (Redis pub/sub, etc), juste un polling DB léger :
    suffisant pour un état affiché dans l'UI, pas conçu pour du temps réel à
    grande échelle."""
    last_payload: str | None = None
    while True:
        dossier = await repository.get(dossier_id)
        if dossier is None:
            yield 'event: error\ndata: {"detail": "Dossier introuvable"}\n\n'
            return
        payload = json.dumps(DossierOut.model_validate(dossier).model_dump(mode="json"))
        if payload != last_payload:
            yield f"event: execution-update\ndata: {payload}\n\n"
            last_payload = payload
        if dossier.status in _TERMINAL_STATUSES or not _has_active_work(dossier):
            yield "event: done\ndata: {}\n\n"
            return
        await asyncio.sleep(1)


@router.get("/{dossier_id}/stream")
async def stream_dossier_execution(
    dossier_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]
):
    repository = DossierRepository(db)
    await _get_or_404(repository, dossier_id)
    return StreamingResponse(
        _execution_events(repository, dossier_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
