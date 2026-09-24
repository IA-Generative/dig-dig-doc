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

from app.celery_client import (
    dispatch_agent_execution,
    dispatch_chat_response,
    dispatch_classification,
    dispatch_entity_extraction,
    dispatch_text_extraction,
)
from app.connectors import s3_connector
from app.core.security.factory import RequestContext, get_current_user
from app.db import get_db
from app.models.conversation import Conversation, MessageRole
from app.models.dossier import Dossier, DossierStatus, TextExtractionStatus
from app.repositories.analyse_repository import AnalyseRepository
from app.repositories.dossier_repository import DossierRepository
from app.schemas.dossier import (
    ChatEventOut,
    ConversationModelUpdate,
    ConversationOut,
    DossierCreate,
    DossierDocumentLabelIn,
    DossierDocumentOut,
    DossierOut,
    FeedbackIn,
    MessageIn,
    PredictionValidationIn,
    PredictionValidationOut,
)
from app.schemas.pagination import Page

router = APIRouter(prefix="/dossiers", tags=["Dossiers"], dependencies=[Depends(get_current_user)])


async def _get_or_404(repository: DossierRepository, dossier_id: uuid.UUID) -> Dossier:
    dossier = await repository.get(dossier_id)
    if dossier is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dossier introuvable")
    return dossier


@router.get("", response_model=Page[DossierOut])
async def list_dossiers(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Page[DossierOut]:
    dossiers, total = await DossierRepository(db).list_paginated(page=page, page_size=page_size)
    return Page.of(list(dossiers), total=total, page=page, page_size=page_size)


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


@router.put("/{dossier_id}/documents/{document_id}/label", response_model=DossierDocumentOut)
async def set_document_label(
    dossier_id: uuid.UUID,
    document_id: uuid.UUID,
    body: DossierDocumentLabelIn,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    repository = DossierRepository(db)
    document = await repository.get_document(dossier_id, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document introuvable")
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document introuvable")
    page = await repository.get_page(document_id, page_id)
    if page is None or page.screenshot_key is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Capture introuvable")
    data, content_type = await run_in_threadpool(s3_connector.download, page.screenshot_key)
    return Response(content=data, media_type=content_type)


@router.post("/{dossier_id}/launch", response_model=DossierOut)
async def launch_dossier(dossier_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]) -> Dossier:
    dossier_repository = DossierRepository(db)
    dossier = await _get_or_404(dossier_repository, dossier_id)
    analyse = await AnalyseRepository(db).get(dossier.analyse_id)
    if analyse is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Analyse introuvable")
    await dossier_repository.launch(dossier, analyse)
    # Dépose les tâches de classification et d'extraction sur la file
    # agent_execution : le worker traite chaque page (VLM + LLM) et dépose
    # les prédictions via l'API interne. Les tâches sont indépendantes et
    # tournent en parallèle sur la file dédiée.
    dispatch_classification(str(dossier.id))
    dispatch_entity_extraction(str(dossier.id))
    # L'exécution des agents est déposée séparément : elle attend que la
    # classification et l'extraction soient terminées avant de lancer les
    # agents LangGraph (les agents utilisent les prédictions déposées).
    dispatch_agent_execution(str(dossier.id))
    return dossier


@router.post("/{dossier_id}/stop", response_model=DossierOut)
async def stop_dossier(dossier_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]) -> Dossier:
    repository = DossierRepository(db)
    dossier = await _get_or_404(repository, dossier_id)
    await repository.stop(dossier)
    return dossier


@router.get("/{dossier_id}/conversations", response_model=Page[ConversationOut])
async def list_conversations(
    dossier_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Page[ConversationOut]:
    repository = DossierRepository(db)
    await _get_or_404(repository, dossier_id)
    conversations, total = await repository.list_conversations_paginated(
        dossier_id=dossier_id, user_id=user.user_id, page=page, page_size=page_size
    )
    items = [_attach_feedbacks(c, user.user_id) for c in conversations]
    return Page.of(items, total=total, page=page, page_size=page_size)


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
    conversation = await repository.create_conversation(dossier_id, user.user_id)
    return _attach_feedbacks(conversation, user.user_id)


@router.delete(
    "/{dossier_id}/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_conversation(
    dossier_id: uuid.UUID,
    conversation_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
):
    repository = DossierRepository(db)
    await _get_or_404(repository, dossier_id)
    conversation = await repository.get_conversation(conversation_id)
    if conversation is None or conversation.dossier_id != dossier_id or conversation.user_id != user.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation introuvable")
    await repository.delete_conversation(conversation)


@router.put(
    "/{dossier_id}/conversations/{conversation_id}/model",
    response_model=ConversationOut,
)
async def update_conversation_model(
    dossier_id: uuid.UUID,
    conversation_id: uuid.UUID,
    body: ConversationModelUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
):
    repository = DossierRepository(db)
    await _get_or_404(repository, dossier_id)
    conversation = await repository.get_conversation(conversation_id)
    if conversation is None or conversation.dossier_id != dossier_id or conversation.user_id != user.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation introuvable")
    conversation = await repository.update_conversation_model(conversation, body.model)
    return _attach_feedbacks(conversation, user.user_id)


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
    if conversation is None or conversation.dossier_id != dossier_id or conversation.user_id != user.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation introuvable")
    # Nettoie les événements de chat de l'exécution précédente : le
    # frontend SSE ne doit voir que les événements de cette nouvelle
    # exécution, pas ceux d'un run précédent.
    await repository.delete_chat_events(conversation_id)
    conversation = await repository.add_message(conversation, MessageRole.USER, body.content)
    # Déclenche la tâche Celery de réponse au chat : le worker charge
    # l'historique + les synthèses, exécute le graphe LangGraph, dépose
    # les événements intermédiaires (chat_events) et le message assistant
    # final (avec sources) via l'API interne.
    dispatch_chat_response(str(conversation_id), str(dossier_id))
    return _attach_feedbacks(conversation, user.user_id)


def _attach_feedbacks(conversation: Conversation, user_id: str) -> Conversation:
    """Filtre les feedbacks de chaque message pour ne garder que celui de
    l'utilisateur courant (MessageOut.feedback)."""
    for message in conversation.messages:
        message.feedback = next((f for f in message.feedbacks if f.user_id == user_id), None)
    return conversation


@router.put(
    "/{dossier_id}/conversations/{conversation_id}/messages/{message_id}/feedback",
    response_model=ConversationOut,
)
async def set_message_feedback(
    dossier_id: uuid.UUID,
    conversation_id: uuid.UUID,
    message_id: uuid.UUID,
    body: FeedbackIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
):
    repository = DossierRepository(db)
    await _get_or_404(repository, dossier_id)
    conversation = await repository.get_conversation(conversation_id)
    if conversation is None or conversation.dossier_id != dossier_id or conversation.user_id != user.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation introuvable")
    message = next((m for m in conversation.messages if m.id == message_id), None)
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message introuvable")
    conversation = await repository.set_feedback(message, user.user_id, body.value, body.reasons, body.comment)
    return _attach_feedbacks(conversation, user.user_id)


@router.delete(
    "/{dossier_id}/conversations/{conversation_id}/messages/{message_id}/feedback",
    response_model=ConversationOut,
)
async def delete_message_feedback(
    dossier_id: uuid.UUID,
    conversation_id: uuid.UUID,
    message_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
):
    repository = DossierRepository(db)
    await _get_or_404(repository, dossier_id)
    conversation = await repository.get_conversation(conversation_id)
    if conversation is None or conversation.dossier_id != dossier_id or conversation.user_id != user.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation introuvable")
    message = next((m for m in conversation.messages if m.id == message_id), None)
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message introuvable")
    conversation = await repository.delete_feedback(message, user.user_id)
    return _attach_feedbacks(conversation, user.user_id)


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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document introuvable")
    page = await repository.get_page(document_id, page_id)
    prediction = await repository.get_prediction(page_id, prediction_id) if page else None
    if page is None or prediction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prédiction introuvable")
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
    return any(doc.text_extraction_status in _EXTRACTION_IN_PROGRESS for doc in dossier.documents)


async def _execution_events(repository: DossierRepository, dossier_id: uuid.UUID) -> AsyncIterator[str]:
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
async def stream_dossier_execution(dossier_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]):
    repository = DossierRepository(db)
    await _get_or_404(repository, dossier_id)
    return StreamingResponse(
        _execution_events(repository, dossier_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# --- SSE : streaming des événements de chat ---
#
# Le frontend s'abonne à ce flux après avoir envoyé un message utilisateur.
# Le worker dépose des chat_events (tool_call, tool_result, thinking, done,
# error) en base pendant l'exécution du graphe LangGraph ; ce flux les
# relaie au navigateur via SSE, en pollant la base (même pattern que
# _execution_events pour le streaming d'exécution de dossier).


async def _chat_events(
    repository: DossierRepository,
    conversation_id: uuid.UUID,
    user_id: str,
) -> AsyncIterator[str]:
    """Émet les événements de chat via SSE, jusqu'à recevoir l'événement
    `done` ou `error` qui marque la fin de l'exécution. Polling DB léger
    (500ms) : suffisant pour une UI réactive sans infrastructure de
    pub/sub."""
    last_seen_id: uuid.UUID | None = None
    while True:
        # Vérifie que la conversation appartient toujours à l'utilisateur
        # (sécurité : le SSE est authentifié mais on vérifie à chaque poll).
        conversation = await repository.get_conversation(conversation_id)
        if conversation is None or conversation.user_id != user_id:
            yield 'event: error\ndata: {"detail": "Conversation introuvable"}\n\n'
            return

        events = await repository.list_chat_events(conversation_id, after_id=last_seen_id)
        for event in events:
            last_seen_id = event.id
            payload = ChatEventOut.model_validate(event).model_dump(mode="json")
            data = json.dumps(payload)
            yield f"event: chat-event\ndata: {data}\n\n"
            # L'événement `done` ou `error` marque la fin du flux.
            if event.kind in ("done", "error"):
                return
        await asyncio.sleep(0.5)


@router.get(
    "/{dossier_id}/conversations/{conversation_id}/stream",
)
async def stream_chat_events(
    dossier_id: uuid.UUID,
    conversation_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
):
    """Flux SSE des événements de chat : le frontend s'y abonne après avoir
    envoyé un message utilisateur pour suivre l'exécution du graphe LangGraph
    en temps réel (appels d'outils, résultats, étapes intermédiaires)."""
    repository = DossierRepository(db)
    await _get_or_404(repository, dossier_id)
    conversation = await repository.get_conversation(conversation_id)
    if conversation is None or conversation.dossier_id != dossier_id or conversation.user_id != user.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation introuvable")
    return StreamingResponse(
        _chat_events(repository, conversation_id, user.user_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
