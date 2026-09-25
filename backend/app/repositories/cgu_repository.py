import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import func, select, update

from app.db import async_session_factory
from app.models.cgu import Cgu


class CguRepository:
    """Accès aux versions des CGU.

    Une seule version est active à la fois. L'activation d'une version
    désactive automatiquement toutes les autres (via une requête UPDATE
    dédiée avant le commit).
    """

    def __init__(self, db) -> None:  # type: ignore[no-untyped-def]
        self.db = db

    async def get_active(self) -> Cgu | None:
        result = await self.db.execute(select(Cgu).where(Cgu.is_active.is_(True)))
        return result.scalar_one_or_none()

    async def get(self, cgu_id: uuid.UUID) -> Cgu | None:
        result = await self.db.execute(select(Cgu).where(Cgu.id == cgu_id))
        return result.scalar_one_or_none()

    async def list_all(self) -> Sequence[Cgu]:
        result = await self.db.execute(select(Cgu).order_by(Cgu.version.desc()))
        return result.scalars().all()

    async def _next_version(self) -> int:
        """Calcule le prochain numéro de version (max + 1, ou 1 si vide)."""
        result = await self.db.execute(select(func.max(Cgu.version)))
        current = result.scalar()
        return (current or 0) + 1

    async def create(self, *, content: str, created_by: str | None = None) -> Cgu:
        version = await self._next_version()
        cgu = Cgu(
            content=content,
            version=version,
            is_active=False,
            created_by=created_by,
        )
        self.db.add(cgu)
        await self.db.commit()
        await self.db.refresh(cgu)
        return cgu

    async def activate(self, cgu: Cgu) -> Cgu:
        """Active une version et désactive toutes les autres."""
        # Désactive toutes les versions existantes en une seule requête.
        await self.db.execute(update(Cgu).values(is_active=False, published_at=None))
        # Active la version demandée.
        cgu.is_active = True
        cgu.published_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(cgu)
        return cgu

    async def update_content(self, cgu: Cgu, content: str) -> Cgu:
        """Met à jour le contenu d'une version non encore publiée."""
        cgu.content = content
        await self.db.commit()
        await self.db.refresh(cgu)
        return cgu


async def get_active_cgu_content() -> str | None:
    """Récupère le contenu de la CGU active sans session DB explicite.

    Utilisé par les routes publiques qui n'ont pas besoin de transaction
    explicite — une session jetable suffit.
    """
    async with async_session_factory() as db:
        cgu = await CguRepository(db).get_active()
        return cgu.content if cgu else None
