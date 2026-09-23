import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.conversation import Message


class FeedbackValue(enum.StrEnum):
    UP = "up"
    DOWN = "down"


class FeedbackReasonCode(enum.StrEnum):
    INCORRECT_ANSWER = "incorrect_answer"
    NOT_USEFUL = "not_useful"
    QUESTIONABLE_SOURCES = "questionable_sources"
    INAPPROPRIATE_TONE = "inappropriate_tone"
    OTHER = "other"


class Feedback(UUIDMixin, TimestampMixin, Base):
    """Retour (pouce haut/bas) d'un utilisateur sur un message de conversation.

    Un seul par (message, utilisateur) - mis à jour sur re-soumission plutôt
    que dupliqué, même principe que la conversation elle-même (voir
    Conversation.uq_conversations_dossier_id_user_id)."""

    __tablename__ = "feedbacks"
    __table_args__ = (UniqueConstraint("message_id", "user_id", name="uq_feedbacks_message_id_user_id"),)

    message_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Identité Keycloak de l'auteur du retour.
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    # Toujours renseigné : un retour est soit un pouce haut, soit un pouce
    # bas, jamais "vide" (les raisons ci-dessous ne sont pertinentes que
    # pour un pouce bas, mais la polarité elle-même n'est jamais optionnelle).
    value: Mapped[FeedbackValue] = mapped_column(Enum(FeedbackValue, name="feedback_value"), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    message: Mapped["Message"] = relationship(back_populates="feedbacks")
    reason_rows: Mapped[list["FeedbackReason"]] = relationship(back_populates="feedback", cascade="all, delete-orphan")

    @property
    def reasons(self) -> list[FeedbackReasonCode]:
        return [row.reason for row in self.reason_rows]


class FeedbackReason(Base):
    """Table de détail : les raisons (multiples) associées à un retour."""

    __tablename__ = "feedback_reasons"

    feedback_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("feedbacks.id", ondelete="CASCADE"), primary_key=True
    )
    reason: Mapped[FeedbackReasonCode] = mapped_column(
        Enum(FeedbackReasonCode, name="feedback_reason_code"), primary_key=True
    )

    feedback: Mapped["Feedback"] = relationship(back_populates="reason_rows")
