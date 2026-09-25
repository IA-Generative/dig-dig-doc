from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_preference import UserPreference


class UserPreferenceRepository:
    """Accès aux préférences utilisateur (thème DSFR, etc.).

    Une ligne par user_id (sub Keycloak). Créée à la volée au premier
    accès si elle n'existe pas encore.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_or_create(self, *, user_id: str) -> UserPreference:
        """Retourne les préférences d'un utilisateur, en créant une ligne
        par défaut si nécessaire."""
        result = await self.db.execute(
            select(UserPreference).where(UserPreference.user_id == user_id)
        )
        record = result.scalar_one_or_none()
        if record is not None:
            return record

        record = UserPreference(user_id=user_id)
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def update_theme(self, *, user_id: str, theme: str) -> UserPreference:
        """Met à jour le thème d'un utilisateur (light/dark/system)."""
        record = await self.get_or_create(user_id=user_id)
        record.theme = theme
        await self.db.commit()
        await self.db.refresh(record)
        return record
