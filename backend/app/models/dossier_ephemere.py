import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.dossier import Dossier


class DossierEphemere(TimestampMixin, Base):
    """Association 1-1 avec Dossier (le run) : marque un dossier comme créé
    via l'API éphémère (persist=false) et porte son TTL. Une Dossier sans
    ligne ici est un dossier classique de la plateforme, comportement
    inchangé. expires_at reste NULL tant que le Dossier n'a pas atteint un
    statut terminal (le TTL démarre à la fin de l'analyse, pas à la
    création) - voir docs/ephemeral-api.md."""

    __tablename__ = "dossier_ephemeres"

    dossier_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("dossiers.id", ondelete="CASCADE"), primary_key=True
    )
    # NULL si le run référence une Analyse classique de la plateforme plutôt
    # qu'une analyse elle-même éphémère (flux B, cf. docs/ephemeral-api.md).
    analyse_ephemere_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("analyse_ephemeres.analyse_id", ondelete="SET NULL"), nullable=True
    )
    persist: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ttl_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    dossier: Mapped["Dossier"] = relationship()
