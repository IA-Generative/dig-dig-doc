"""Routes internes pour l'agent helper (issue #50).

Deux familles de routes, toutes appelées par le worker `agent_execution`
(pas le navigateur, même auth que app/routers/internal.py) :

- `agent_conversations_router` (`/internal/agent-conversations/*`) : lecture
  de l'historique + dépôt du message assistant final et des chat_events
  (streaming), sur le modèle de la section conversation de
  app/routers/internal.py.
- `router` (`/internal/agent/*`) : les "tools" de l'agent (recherche/
  création d'analyses et de dossiers, lancement du pipeline). Plutôt que
  dupliquer la logique métier, ces routes appellent directement les
  fonctions des routers REST classiques (`app/routers/analyses.py`,
  `app/routers/dossiers.py`) avec juste `db` - ces ressources n'ont pas de
  notion d'identité utilisateur (voir docs/mcp-helper-agent-plan.md,
  "Découvertes clés"), donc pas besoin de RequestContext factice. Le
  serveur MCP helper (`app/mcp/helper_server.py`, à venir) appellera ces
  mêmes fonctions de router in-process ; le worker, qui n'a pas d'accès DB,
  passe par ici en HTTP.
"""

import base64
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.celery_client import dispatch_text_extraction
from app.connectors import s3_connector
from app.core.security.internal import verify_app_token
from app.db import get_db
from app.models.agent_conversation import AgentMessageRole
from app.repositories.agent_conversation_repository import AgentConversationRepository
from app.repositories.dossier_repository import DossierRepository
from app.routers.analyses import create_analyse as _create_analyse
from app.routers.analyses import get_analyse as _get_analyse
from app.routers.analyses import list_analyses as _list_analyses
from app.routers.dossiers import _get_or_404 as _get_dossier_or_404
from app.routers.dossiers import create_dossier as _create_dossier
from app.routers.dossiers import get_dossier as _get_dossier
from app.routers.dossiers import launch_dossier as _launch_dossier
from app.routers.dossiers import list_dossiers as _list_dossiers
from app.schemas.agent_conversation import (
    AgentChatEventIn,
    AgentChatEventOut,
    InternalAgentConversationOut,
    InternalAgentMessageIn,
    InternalAgentMessageOut,
)
from app.schemas.analyse import AnalyseCreate, AnalyseListItem, AnalyseOut
from app.schemas.dossier import DossierCreate, DossierOut
from app.schemas.pagination import Page

agent_conversations_router = APIRouter(
    prefix="/internal/agent-conversations", tags=["Internal", "Agent"], dependencies=[Depends(verify_app_token)]
)
router = APIRouter(prefix="/internal/agent", tags=["Internal", "Agent"], dependencies=[Depends(verify_app_token)])


# --- Conversations (historique, chat_events, message assistant final) ---


@agent_conversations_router.get("/{conversation_id}", response_model=InternalAgentConversationOut)
async def get_internal_agent_conversation(conversation_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]):
    """Historique user/assistant pour le worker - les tool_call/tool_result
    déjà journalisés ne sont pas renvoyés (le graphe reconstruit son propre
    raisonnement à chaque tour, seul le dialogue en langage naturel compte)."""
    conversation = await AgentConversationRepository(db).get(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation introuvable")
    dialogue_roles = {AgentMessageRole.USER, AgentMessageRole.ASSISTANT}
    return InternalAgentConversationOut(
        id=conversation.id,
        created_by=conversation.created_by,
        messages=[
            InternalAgentMessageOut.model_validate(m) for m in conversation.messages if m.role in dialogue_roles
        ],
    )


@agent_conversations_router.post(
    "/{conversation_id}/chat-events",
    response_model=AgentChatEventOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_agent_chat_event(
    conversation_id: uuid.UUID,
    body: AgentChatEventIn,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    repository = AgentConversationRepository(db)
    conversation = await repository.get(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation introuvable")
    return await repository.add_chat_event(conversation_id, body.kind, body.data)


@agent_conversations_router.post("/{conversation_id}/messages")
async def add_agent_assistant_message(
    conversation_id: uuid.UUID,
    body: InternalAgentMessageIn,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    repository = AgentConversationRepository(db)
    conversation = await repository.get(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation introuvable")
    await repository.add_message(
        conversation,
        AgentMessageRole.ASSISTANT,
        content=body.content,
        sources=[s.model_dump() for s in body.sources],
    )
    return {"ok": True}


# --- Tools : analyses ---


@router.get("/analyses", response_model=Page[AnalyseListItem])
async def list_agent_analyses(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    q: str | None = None,
) -> Page[AnalyseListItem]:
    return await _list_analyses(db, page=page, page_size=page_size, q=q)


@router.get("/analyses/{analyse_id}", response_model=AnalyseOut)
async def get_agent_analyse(analyse_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]) -> AnalyseOut:
    return await _get_analyse(analyse_id, db)


@router.post("/analyses", response_model=AnalyseOut, status_code=status.HTTP_201_CREATED)
async def create_agent_analyse(body: AnalyseCreate, db: Annotated[AsyncSession, Depends(get_db)]) -> AnalyseOut:
    return await _create_analyse(body, db)


# --- Tools : dossiers ---


@router.get("/dossiers", response_model=Page[DossierOut])
async def list_agent_dossiers(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Page[DossierOut]:
    return await _list_dossiers(db, page=page, page_size=page_size)


@router.get("/dossiers/{dossier_id}", response_model=DossierOut)
async def get_agent_dossier(dossier_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]) -> DossierOut:
    return await _get_dossier(dossier_id, db)


@router.post("/dossiers", response_model=DossierOut, status_code=status.HTTP_201_CREATED)
async def create_agent_dossier(body: DossierCreate, db: Annotated[AsyncSession, Depends(get_db)]) -> DossierOut:
    return await _create_dossier(body, db)


class AgentDossierFileIn(BaseModel):
    name: str
    content_base64: str
    mimetype: str = "application/octet-stream"


class AgentDossierFilesIn(BaseModel):
    files: list[AgentDossierFileIn]


@router.post("/dossiers/{dossier_id}/documents", response_model=DossierOut)
async def add_agent_dossier_files(
    dossier_id: uuid.UUID,
    body: AgentDossierFilesIn,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Équivalent de POST /dossiers/{id}/documents, mais en base64 dans un
    corps JSON plutôt qu'en multipart : le worker n'a pas d'UploadFile
    FastAPI, seulement des octets décodés (même raison que
    app/routers/ephemeral.py::_create_run)."""
    repository = DossierRepository(db)
    dossier = await _get_dossier_or_404(repository, dossier_id)
    documents = []
    for f in body.files:
        data = base64.b64decode(f.content_base64)
        s3_key = f"dossiers/{dossier_id}/{uuid.uuid4()}-{f.name or 'document'}"
        await run_in_threadpool(s3_connector.upload, s3_key, data, f.mimetype)
        documents.append({"name": f.name or "document", "size": len(data), "s3_key": s3_key, "mimetype": f.mimetype})
    created = await repository.add_documents(dossier, documents)
    for document in created:
        dispatch_text_extraction(str(document.id))
    return await _get_dossier_or_404(repository, dossier_id)


@router.post("/dossiers/{dossier_id}/launch", response_model=DossierOut)
async def launch_agent_dossier(dossier_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]) -> DossierOut:
    return await _launch_dossier(dossier_id, db)
