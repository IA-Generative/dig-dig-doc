import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class CguAcceptance(UUIDMixin, TimestampMixin, Base):
    """Trace l'acceptation d'une version des CGU par un utilisateur.

    Une ligne par couple (user_id, cgu_id). L'unicité est garantie par
    une contrainte : un utilisateur ne peut pas accepter deux fois la
    même version. Quand une nouvelle version des CGU est activée par
    l'administrateur, les utilisateurs doivent l'accepter à nouveau
    pour continuer à utiliser l'application.
    """

    __tablename__ = "cgu_acceptances"
    __table_args__ = (UniqueConstraint("user_id", "cgu_id", name="uq_cgu_acceptance_user_cgu"),)

    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    cgu_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cgus.id", ondelete="CASCADE"), nullable=False
    )
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
