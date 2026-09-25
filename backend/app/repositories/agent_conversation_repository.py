import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.agent_chat_event import AgentChatEvent, AgentChatEventKind
from app.models.agent_conversation import (
    AgentConversation,
    AgentMessage,
    AgentMessageRole,
    AgentMessageSource,
)


class AgentConversationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _conversation_query(self):
        # populate_existing: sans ça, une AgentConversation déjà dans
        # l'identity map (ex. juste après y avoir ajouté un message) garderait
        # sa collection `messages` périmée au lieu de reprendre la ligne
        # tout juste committée (même raison que DossierRepository._conversation_query).
        return (
            select(AgentConversation)
            .options(selectinload(AgentConversation.messages).selectinload(AgentMessage.sources))
            .execution_options(populate_existing=True)
        )

    async def list_for_user_paginated(
        self, *, created_by: str, page: int, page_size: int
    ) -> tuple[Sequence[AgentConversation], int]:
        base = self._conversation_query().where(AgentConversation.created_by == created_by)
        count_query = (
            select(func.count()).select_from(AgentConversation).where(AgentConversation.created_by == created_by)
        )
        total = await self.db.scalar(count_query)
        result = await self.db.execute(
            base.order_by(AgentConversation.created_at.desc()).limit(page_size).offset((page - 1) * page_size)
        )
        return result.scalars().all(), total or 0

    async def get(self, conversation_id: uuid.UUID) -> AgentConversation | None:
        result = await self.db.execute(self._conversation_query().where(AgentConversation.id == conversation_id))
        return result.scalar_one_or_none()

    async def create(self, created_by: str, title: str | None = None) -> AgentConversation:
        conversation = AgentConversation(created_by=created_by, title=title)
        self.db.add(conversation)
        await self.db.commit()
        await self.db.refresh(conversation)
        return await self.get(conversation.id)

    async def delete(self, conversation: AgentConversation) -> None:
        await self.db.delete(conversation)
        await self.db.commit()

    async def add_message(
        self,
        conversation: AgentConversation,
        role: AgentMessageRole,
        *,
        content: str | None = None,
        tool_name: str | None = None,
        data: dict | None = None,
        sources: list[dict] | None = None,
    ) -> AgentConversation:
        message = AgentMessage(
            agent_conversation_id=conversation.id,
            role=role,
            content=content,
            tool_name=tool_name,
            data=data or {},
        )
        self.db.add(message)
        await self.db.flush()
        for source in sources or []:
            self.db.add(
                AgentMessageSource(
                    message_id=message.id,
                    dossier_id=source.get("dossier_id"),
                    analyse_id=source.get("analyse_id"),
                    excerpt=source.get("excerpt"),
                )
            )
        await self.db.commit()
        return await self.get(conversation.id)

    # --- Événements de chat (streaming de l'exécution du graphe interne) ---

    async def add_chat_event(self, conversation_id: uuid.UUID, kind: AgentChatEventKind, data: dict) -> AgentChatEvent:
        event = AgentChatEvent(agent_conversation_id=conversation_id, kind=kind, data=data)
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        return event

    async def list_chat_events(
        self, conversation_id: uuid.UUID, after_id: uuid.UUID | None = None
    ) -> Sequence[AgentChatEvent]:
        stmt = (
            select(AgentChatEvent)
            .where(AgentChatEvent.agent_conversation_id == conversation_id)
            .order_by(AgentChatEvent.created_at, AgentChatEvent.id)
        )
        if after_id is not None:
            sub = select(AgentChatEvent.created_at).where(AgentChatEvent.id == after_id).scalar_subquery()
            stmt = stmt.where(AgentChatEvent.created_at > sub)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def delete_chat_events(self, conversation_id: uuid.UUID) -> None:
        await self.db.execute(
            AgentChatEvent.__table__.delete().where(AgentChatEvent.agent_conversation_id == conversation_id)
        )
        await self.db.commit()
