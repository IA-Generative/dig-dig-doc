"""Événements d'exécution du graphe LangGraph de l'agent helper (streaming).

Pendant à ChatEvent (app/models/chat_event.py), mais rattaché à une
AgentConversation plutôt qu'à une Conversation de dossier - consommé par le
frontend via SSE (GET /agent-conversations/{id}/stream).
"""

import enum
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Enum, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.agent_conversation import AgentConversation


class AgentChatEventKind(enum.StrEnum):
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    THINKING = "thinking"
    DONE = "done"
    ERROR = "error"


class AgentChatEvent(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "agent_chat_events"

    agent_conversation_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("agent_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind: Mapped[AgentChatEventKind] = mapped_column(
        Enum(AgentChatEventKind, name="agent_chat_event_kind"), nullable=False
    )
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    conversation: Mapped["AgentConversation"] = relationship(back_populates="chat_events")
