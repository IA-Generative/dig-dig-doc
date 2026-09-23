"""Événements d'exécution du chat (streaming).

Ces événements sont déposés par le worker pendant l'exécution du graphe
LangGraph de chat (appels d'outils, résultats, étapes intermédiaires) et
consommés par le frontend via SSE (GET /dossiers/{id}/conversations/{cid}/stream).
Ils sont éphémères : leur seul but est de streamer la progression de
l'exécution en temps réel. Le message assistant final (avec sources) est
déposé séparément via POST /internal/conversations/{id}/messages.
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
    from app.models.conversation import Conversation


class ChatEventKind(enum.StrEnum):
    """Type d'événement produit pendant l'exécution du chat."""

    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    THINKING = "thinking"
    DONE = "done"
    ERROR = "error"


class ChatEvent(UUIDMixin, TimestampMixin, Base):
    """Un événement d'exécution du chat, déposé par le worker et streamé
    au frontend via SSE. Le payload (data) est flexible (JSONB) pour
    s'adapter à chaque type d'événement."""

    __tablename__ = "chat_events"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind: Mapped[ChatEventKind] = mapped_column(
        Enum(ChatEventKind, name="chat_event_kind"), nullable=False
    )
    # Payload flexible : {tool_name, arguments} pour tool_call,
    # {tool_name, preview} pour tool_result, {message} pour thinking/error,
    # {message_id} pour done.
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    conversation: Mapped["Conversation"] = relationship(back_populates="chat_events")
