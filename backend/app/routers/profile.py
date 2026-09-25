from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.factory import RequestContext, get_current_user
from app.db import get_db
from app.models.agent_conversation import AgentConversation, AgentMessage, AgentMessageRole
from app.models.analyse_share import AnalyseShare
from app.models.conversation import Conversation, Message, MessageRole
from app.repositories.user_preference_repository import UserPreferenceRepository
from app.schemas.profile import UserPreferenceOut, UserPreferenceUpdate, UserStats

router = APIRouter(prefix="/me", tags=["Profile"], dependencies=[Depends(get_current_user)])

VALID_THEMES = {"light", "dark", "system"}


@router.get("/preferences", response_model=UserPreferenceOut)
async def get_preferences(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
) -> UserPreferenceOut:
    """Retourne les préférences de l'utilisateur courant (créées à la volée)."""
    record = await UserPreferenceRepository(db).get_or_create(user_id=user.user_id)
    return UserPreferenceOut(theme=record.theme)


@router.patch("/preferences", response_model=UserPreferenceOut)
async def update_preferences(
    body: UserPreferenceUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
) -> UserPreferenceOut:
    """Met à jour les préférences de l'utilisateur courant."""
    if body.theme not in VALID_THEMES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Thème invalide: {body.theme}. Valeurs acceptées: light, dark, system.",
        )
    record = await UserPreferenceRepository(db).update_theme(user_id=user.user_id, theme=body.theme)
    return UserPreferenceOut(theme=record.theme)


@router.get("/stats", response_model=UserStats)
async def get_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
) -> UserStats:
    """Statistiques personnelles de l'utilisateur courant."""
    user_id = user.user_id

    # Conversations (chat dossier)
    conversations_count = await db.scalar(
        select(func.count()).select_from(Conversation).where(Conversation.user_id == user_id)
    )

    # Messages envoyés dans les conversations de dossier
    messages_sent_count = await db.scalar(
        select(func.count())
        .select_from(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(Conversation.user_id == user_id, Message.role == MessageRole.USER)
    )

    # Conversations avec l'agent helper
    agent_conversations_count = await db.scalar(
        select(func.count()).select_from(AgentConversation).where(AgentConversation.created_by == user_id)
    )

    # Messages envoyés à l'agent helper
    agent_messages_sent_count = await db.scalar(
        select(func.count())
        .select_from(AgentMessage)
        .join(AgentConversation, AgentMessage.agent_conversation_id == AgentConversation.id)
        .where(AgentConversation.created_by == user_id, AgentMessage.role == AgentMessageRole.USER)
    )

    # Dossiers distincts accessibles (via conversations)
    dossiers_count = await db.scalar(
        select(func.count(func.distinct(Conversation.dossier_id)))
        .select_from(Conversation)
        .where(Conversation.user_id == user_id)
    )

    # Analyses partagées par l'utilisateur
    analyses_shared_count = await db.scalar(
        select(func.count()).select_from(AnalyseShare).where(AnalyseShare.created_by == user_id)
    )

    # Dernière activité : max(created_at) sur les messages des deux types de conversations
    last_msg_conv = await db.scalar(
        select(func.max(Message.created_at))
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(Conversation.user_id == user_id)
    )
    last_msg_agent = await db.scalar(
        select(func.max(AgentMessage.created_at))
        .join(AgentConversation, AgentMessage.agent_conversation_id == AgentConversation.id)
        .where(AgentConversation.created_by == user_id)
    )
    last_activity_at = None
    if last_msg_conv and last_msg_agent:
        last_activity_at = max(last_msg_conv, last_msg_agent)
    elif last_msg_conv:
        last_activity_at = last_msg_conv
    elif last_msg_agent:
        last_activity_at = last_msg_agent

    return UserStats(
        conversations_count=conversations_count or 0,
        messages_sent_count=messages_sent_count or 0,
        agent_conversations_count=agent_conversations_count or 0,
        agent_messages_sent_count=agent_messages_sent_count or 0,
        dossiers_count=dossiers_count or 0,
        analyses_shared_count=analyses_shared_count or 0,
        last_activity_at=last_activity_at,
    )
