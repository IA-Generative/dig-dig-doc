import uuid

from sqlalchemy import select

from app.models.cgu_acceptance import CguAcceptance


class CguAcceptanceRepository:
    """Accès aux acceptations des CGU par les utilisateurs.

    Une ligne par couple (user_id, cgu_id). Permet de vérifier si un
    utilisateur a accepté la version active des CGU.
    """

    def __init__(self, db) -> None:  # type: ignore[no-untyped-def]
        self.db = db

    async def has_accepted(self, *, user_id: str, cgu_id: uuid.UUID) -> bool:
        """Vérifie si l'utilisateur a accepté la version donnée des CGU."""
        result = await self.db.execute(
            select(CguAcceptance.id).where(
                CguAcceptance.user_id == user_id,
                CguAcceptance.cgu_id == cgu_id,
            )
        )
        return result.scalar_one_or_none() is not None

    async def accept(self, *, user_id: str, cgu_id: uuid.UUID) -> CguAcceptance:
        """Enregistre l'acceptation d'une version des CGU par un utilisateur.

        Idempotente : si l'utilisateur a déjà accepté cette version, on
        retourne l'enregistrement existant sans lever d'erreur.
        """
        existing = await self.db.execute(
            select(CguAcceptance).where(
                CguAcceptance.user_id == user_id,
                CguAcceptance.cgu_id == cgu_id,
            )
        )
        record = existing.scalar_one_or_none()
        if record is not None:
            return record

        record = CguAcceptance(user_id=user_id, cgu_id=cgu_id)
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        return record
