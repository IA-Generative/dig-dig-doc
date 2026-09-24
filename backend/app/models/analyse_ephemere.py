import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.analyse import Analyse


class AnalyseEphemere(TimestampMixin, Base):
    """Association 1-1 avec Analyse : marque une analyse comme créée via
    l'API éphémère (persist=false) et porte son TTL. Une Analyse sans ligne
    ici est une analyse classique de la plateforme, comportement inchangé."""

    __tablename__ = "analyse_ephemeres"

    analyse_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("analyses.id", ondelete="CASCADE"), primary_key=True
    )
    persist: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Mis à jour à chaque fin de run référençant cette analyse ; expires_at en
    # découle (last_run_ended_at + ttl_hours du run). Voir docs/ephemeral-api.md.
    last_run_ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    analyse: Mapped["Analyse"] = relationship()
