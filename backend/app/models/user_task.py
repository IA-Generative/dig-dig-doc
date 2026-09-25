import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class UserTaskKind(enum.StrEnum):
    """Type de tâche asynchrone lancée par un utilisateur."""

    TEXT_EXTRACTION = "text_extraction"
    CLASSIFICATION = "classification"
    ENTITY_EXTRACTION = "entity_extraction"
    AGENT_EXECUTION = "agent_execution"
    CHAT_RESPONSE = "chat_response"
    HELPER_CHAT = "helper_chat"
    DOCUMENT_SUMMARY = "document_summary"
    DOSSIER_SUMMARY = "dossier_summary"
    ANALYSE_SUGGESTION = "analyse_suggestion"


class UserTaskStatus(enum.StrEnum):
    """Cycle de vie d'une tâche utilisateur.

    PENDING → RUNNING → SUCCESS / FAILURE
    """

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"


class UserTask(UUIDMixin, TimestampMixin, Base):
    """Tâche asynchrone lancée par un utilisateur, persistée pour permettre
    un suivi côté frontend (bouton « Tâches en cours », issue #62).

    Une ligne est créée au moment du dispatch Celery, puis mise à jour par
    les workers via l'API interne quand la tâche démarre / se termine.
    Le ``celery_task_id`` permet de faire le lien avec Celery (AsyncResult)
    si un result backend est configuré plus tard.
    """

    __tablename__ = "user_tasks"

    user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    kind: Mapped[UserTaskKind] = mapped_column(
        Enum(UserTaskKind, name="user_task_kind"), nullable=False
    )
    status: Mapped[UserTaskStatus] = mapped_column(
        Enum(UserTaskStatus, name="user_task_status"),
        nullable=False,
        default=UserTaskStatus.PENDING,
    )
    # Identifiant de la tâche Celery (retourné par send_task), pour faire le
    # lien avec le broker si besoin. Peut être null si le dispatch échoue.
    celery_task_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)

    # Libellé lisible affiché dans l'UI (ex: « Classification du dossier
    # « Impôts 2024 » »). Construit par le router au moment du dispatch.
    label: Mapped[str] = mapped_column(String, nullable=False)

    # Lien optionnel vers l'élément concerné (dossier, analyse,
    # conversation). On stocke l'UUID en string plutôt qu'en ForeignKey car
    # la tâche peut concerner différents types d'objets et que la suppression
    # d'un dossier ne doit pas effacer l'historique des tâches.
    target_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    # Type de la cible (dossier, analyse, conversation, agent_conversation)
    # pour construire le lien côté frontend.
    target_type: Mapped[str | None] = mapped_column(String, nullable=True)

    # Message d'erreur si status == FAILURE
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Horodatage du passage en RUNNING (distinct de created_at qui marque
    # la création de la ligne = dispatch).
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Horodatage de la fin (SUCCESS ou FAILURE).
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
