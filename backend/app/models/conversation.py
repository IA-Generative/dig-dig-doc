import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.dossier import Dossier, DossierDocument, ExecutionStep


class MessageRole(enum.StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class Conversation(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "conversations"

    dossier_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("dossiers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # L'auteur de la conversation (identité Keycloak) : la page dossier est
    # un chat personnel à chaque instructeur qui l'ouvre.
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)

    dossier: Mapped["Dossier"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at"
    )


class Message(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole, name="message_role"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
    sources: Mapped[list["MessageSource"]] = relationship(
        back_populates="message", cascade="all, delete-orphan", order_by="MessageSource.created_at"
    )


class MessageSource(UUIDMixin, TimestampMixin, Base):
    """Référence utilisée par l'agent pour construire une réponse : un
    document (et éventuellement une étape d'exécution), avec un court
    extrait pour donner le contexte sans rouvrir le document entier."""

    __tablename__ = "message_sources"

    message_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    dossier_document_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("dossier_documents.id", ondelete="SET NULL"), nullable=True
    )
    execution_step_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("execution_steps.id", ondelete="SET NULL"), nullable=True
    )
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)

    message: Mapped["Message"] = relationship(back_populates="sources")
    document: Mapped["DossierDocument | None"] = relationship()
    execution_step: Mapped["ExecutionStep | None"] = relationship()
