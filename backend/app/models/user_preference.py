from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class UserPreference(Base):
    """Préférences utilisateur persistées côté backend (thème DSFR, etc.).

    Une ligne par utilisateur (user_id = sub Keycloak, clé primaire).
    Créée à la volée au premier GET /api/me/preferences si elle n'existe
    pas encore - pas de table Users dédiée, l'identité vient de Keycloak.
    """

    __tablename__ = "user_preferences"

    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    theme: Mapped[str] = mapped_column(String, nullable=False, default="system")
    updated_at: Mapped[str] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
