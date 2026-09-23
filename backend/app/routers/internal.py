import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.internal import verify_app_token
from app.db import get_db
from app.models.conversation import MessageRole
from app.repositories.dossier_repository import DossierRepository
from app.schemas.dossier import (
    BoundingBoxIn,
    BoundingBoxOut,
    ConversationOut,
    DocumentPageIn,
    DocumentPageOut,
    DocumentPredictionIn,
    DocumentPredictionOut,
    DossierDocumentOut,
    ExecutionLogIn,
    ExecutionStepCompleteIn,
    ExecutionStepOut,
    InternalMessageIn,
    TextExtractionStatusIn,
)

# Routes appelées par les workers Celery (pas par le navigateur) : le worker
# dépose ici le résultat de son travail - logs en cours d'exécution, étape
# terminée, pages/prédictions extraites d'un document, réponse de l'agent.
router = APIRouter(prefix="/internal", tags=["Internal"], dependencies=[Depends(verify_app_token)])


@router.post("/execution-steps/{step_id}/logs", response_model=ExecutionStepOut)
async def add_execution_log(step_id: uuid.UUID, body: ExecutionLogIn, db: Annotated[AsyncSession, Depends(get_db)]):
    repository = DossierRepository(db)
    step = await repository.get_execution_step_by_id(step_id)
    if step is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Étape introuvable")
    return await repository.add_log(step, body.level, body.message)


@router.post("/execution-steps/{step_id}/complete", response_model=ExecutionStepOut)
async def complete_execution_step(
    step_id: uuid.UUID, body: ExecutionStepCompleteIn, db: Annotated[AsyncSession, Depends(get_db)]
):
    repository = DossierRepository(db)
    step = await repository.get_execution_step_by_id(step_id)
    if step is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Étape introuvable")
    return await repository.complete_execution_step(step, body.status, body.output)


@router.get("/documents/{document_id}", response_model=DossierDocumentOut)
async def get_document(document_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]):
    document = await DossierRepository(db).get_document_by_id(document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document introuvable")
    return document


@router.put("/documents/{document_id}/extraction-status", response_model=DossierDocumentOut)
async def set_document_extraction_status(
    document_id: uuid.UUID, body: TextExtractionStatusIn, db: Annotated[AsyncSession, Depends(get_db)]
):
    repository = DossierRepository(db)
    document = await repository.get_document_by_id(document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document introuvable")
    await repository.set_text_extraction_status(document, body.status, body.error)
    return document


@router.post("/documents/{document_id}/pages", response_model=DocumentPageOut, status_code=status.HTTP_201_CREATED)
async def add_document_page(document_id: uuid.UUID, body: DocumentPageIn, db: Annotated[AsyncSession, Depends(get_db)]):
    repository = DossierRepository(db)
    document = await repository.get_document_by_id(document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document introuvable")
    return await repository.add_page(
        document,
        page_number=body.page_number,
        width=body.width,
        height=body.height,
        content=body.content,
        screenshot_key=body.screenshot_key,
    )


@router.post("/pages/{page_id}/bounding-boxes", response_model=BoundingBoxOut, status_code=status.HTTP_201_CREATED)
async def add_bounding_box(page_id: uuid.UUID, body: BoundingBoxIn, db: Annotated[AsyncSession, Depends(get_db)]):
    repository = DossierRepository(db)
    page = await repository.get_page_by_id(page_id)
    if page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page introuvable")
    return await repository.add_bounding_box(page, **body.model_dump())


@router.post("/pages/{page_id}/predictions", response_model=DocumentPredictionOut, status_code=status.HTTP_201_CREATED)
async def add_document_prediction(
    page_id: uuid.UUID, body: DocumentPredictionIn, db: Annotated[AsyncSession, Depends(get_db)]
):
    repository = DossierRepository(db)
    page = await repository.get_page_by_id(page_id)
    if page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page introuvable")
    return await repository.add_prediction(
        page,
        kind=body.kind,
        name=body.name,
        value=body.value,
        confidence=body.confidence,
        label_definition_id=body.label_definition_id,
        entity_definition_id=body.entity_definition_id,
        page_ids=body.page_ids,
        bounding_box_ids=body.bounding_box_ids,
    )


@router.post("/conversations/{conversation_id}/messages", response_model=ConversationOut)
async def add_assistant_message(
    conversation_id: uuid.UUID, body: InternalMessageIn, db: Annotated[AsyncSession, Depends(get_db)]
):
    repository = DossierRepository(db)
    conversation = await repository.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation introuvable")
    return await repository.add_message(
        conversation, MessageRole.ASSISTANT, body.content, sources=[s.model_dump() for s in body.sources]
    )
