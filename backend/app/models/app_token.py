from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class AppToken(UUIDMixin, TimestampMixin, Base):
    """Jeton permettant à une application externe (pas un navigateur, pas de
    compte Keycloak) d'appeler l'API - même principe que le jeton de partage
    d'analyse : seul le hash est stocké, le jeton en clair n'est montré
    qu'à la création. Remplace le secret unique INTERNAL_WORKER_TOKEN par
    plusieurs jetons nommés, révocables indépendamment."""

    __tablename__ = "app_tokens"

    name: Mapped[str] = mapped_column(String, nullable=False)
    token_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
