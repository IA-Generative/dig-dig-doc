"""Conversation avec l'agent helper (issue #50).

Contrairement à `Conversation` (app/models/conversation.py), une
`AgentConversation` n'est rattachée à aucun dossier unique : elle peut en
créer/retrouver plusieurs (ou aucun) au fil de l'échange, via les tools de
l'agent (MCP `/mcp/helper` ou graphe LangGraph interne, voir
docs/mcp-helper-agent-plan.md). Pas de TTL : conservée indéfiniment, comme
les dossiers classiques.
"""

import enum
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.agent_chat_event import AgentChatEvent
    from app.models.analyse import Analyse
    from app.models.dossier import Dossier


class AgentMessageRole(enum.StrEnum):
    """`USER`/`ASSISTANT` : tour de dialogue en langage naturel, affiché
    dans la modal. `TOOL_CALL`/`TOOL_RESULT`/`ERROR` : trace d'exécution
    d'un tool, utile pour l'audit et pour un client MCP externe qui n'a pas
    de tour user/assistant mais journalise quand même ses appels."""

    USER = "user"
    ASSISTANT = "assistant"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ERROR = "error"


class AgentConversation(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "agent_conversations"

    # user_id Keycloak (usage produit) ou identity.id d'un jeton API (usage
    # MCP externe) - même convention que `created_by` sur les ressources
    # éphémères (app/core/security/ephemeral.py).
    created_by: Mapped[str] = mapped_column(String, nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(String, nullable=True)

    messages: Mapped[list["AgentMessage"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="AgentMessage.created_at",
    )
    chat_events: Mapped[list["AgentChatEvent"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="AgentChatEvent.created_at",
    )


class AgentMessage(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "agent_messages"

    agent_conversation_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("agent_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[AgentMessageRole] = mapped_column(Enum(AgentMessageRole, name="agent_message_role"), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Nom du tool pour tool_call/tool_result/error, ex. "create_dossier".
    tool_name: Mapped[str | None] = mapped_column(String, nullable=True)
    # {"arguments": ...} pour tool_call, {"result": ...} pour tool_result/error -
    # même pattern flexible que ChatEvent.data.
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    conversation: Mapped["AgentConversation"] = relationship(back_populates="messages")
    sources: Mapped[list["AgentMessageSource"]] = relationship(
        back_populates="message",
        cascade="all, delete-orphan",
        order_by="AgentMessageSource.created_at",
    )


class AgentMessageSource(UUIDMixin, TimestampMixin, Base):
    """Ressource consultée/produite par l'agent pour construire sa réponse -
    permet le lien direct "ouvrir ce dossier" côté frontend."""

    __tablename__ = "agent_message_sources"

    message_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("agent_messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dossier_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("dossiers.id", ondelete="SET NULL"), nullable=True
    )
    analyse_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("analyses.id", ondelete="SET NULL"), nullable=True
    )
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)

    message: Mapped["AgentMessage"] = relationship(back_populates="sources")
    dossier: Mapped["Dossier | None"] = relationship()
    analyse: Mapped["Analyse | None"] = relationship()
