import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, Enum, ForeignKey, String, Table, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.document_page import BoundingBox, DocumentPage
    from app.models.dossier import Dossier, DossierDocument, ExecutionStep

# Granularité d'une source, du plus large au plus précis : au minimum le
# document (dossier_document_id ci-dessous), éventuellement affinée à un
# ensemble de pages, ou plus précisément à un ensemble de bbox sur ces pages.
message_source_pages = Table(
    "message_source_pages",
    Base.metadata,
    Column(
        "message_source_id",
        PG_UUID(as_uuid=True),
        ForeignKey("message_sources.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "document_page_id", PG_UUID(as_uuid=True), ForeignKey("document_pages.id", ondelete="CASCADE"), primary_key=True
    ),
)

message_source_bounding_boxes = Table(
    "message_source_bounding_boxes",
    Base.metadata,
    Column(
        "message_source_id",
        PG_UUID(as_uuid=True),
        ForeignKey("message_sources.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "bounding_box_id", PG_UUID(as_uuid=True), ForeignKey("bounding_boxes.id", ondelete="CASCADE"), primary_key=True
    ),
)


class MessageRole(enum.StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class Conversation(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "conversations"
    __table_args__ = (UniqueConstraint("dossier_id", "user_id", name="uq_conversations_dossier_id_user_id"),)

    dossier_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("dossiers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # L'auteur de la conversation (identité Keycloak) : la page dossier est
    # un chat personnel à chaque instructeur qui l'ouvre.
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    # Identifiant de modèle tel que renvoyé par GET /models (id du hub LLM
    # configuré) ; NULL = pas de préférence, le hub par défaut sera utilisé.
    model: Mapped[str | None] = mapped_column(String, nullable=True)

    dossier: Mapped["Dossier"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at"
    )

    @property
    def dossier_name(self) -> str:
        return self.dossier.name

    @property
    def last_message_preview(self) -> str | None:
        return self.messages[-1].content if self.messages else None

    @property
    def last_activity_at(self) -> datetime:
        return self.messages[-1].created_at if self.messages else self.created_at


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
    pages: Mapped[list["DocumentPage"]] = relationship(
        secondary=message_source_pages, order_by="DocumentPage.page_number"
    )
    bounding_boxes: Mapped[list["BoundingBox"]] = relationship(
        secondary=message_source_bounding_boxes, order_by="BoundingBox.created_at"
    )
