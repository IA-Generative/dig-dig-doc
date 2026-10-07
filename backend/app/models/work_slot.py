import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class WorkSlot(UUIDMixin, TimestampMixin, Base):
    """Créneau de traitement qu'une personne réserve pour un dossier (issue #174).

    **Privé** : un créneau n'appartient qu'à la personne qui l'a posé, qui est la seule à le lire et à le modifier.
    Il est **toujours rattaché à un dossier**, et il n'y en a qu'un par couple (personne, dossier). Le partage de
    l'agenda avec d'autres personnes viendra plus tard : ``user_id`` en reste le propriétaire.

    Il n'entre pas dans le journal du dossier (#169) : le journal est lu par tous ceux qui ouvrent le dossier,
    alors que la planification de chacun est personnelle."""

    __tablename__ = "work_slots"
    __table_args__ = (UniqueConstraint("user_id", "dossier_id", name="uq_work_slots_user_dossier"),)

    # Identifiant (sub Keycloak) du propriétaire.
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    dossier_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("dossiers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Première occurrence ; les suivantes se déduisent de la récurrence.
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Règle de répétition (unité, intervalle, jours, fin), ou NULL pour un créneau unique.
    recurrence: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Rappels, en minutes avant chaque occurrence (0 = à l'heure).
    reminders: Mapped[list[int]] = mapped_column(JSONB, nullable=False, default=list)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
