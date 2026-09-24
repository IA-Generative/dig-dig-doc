import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analyse_ephemere import AnalyseEphemere
from app.models.dossier_ephemere import DossierEphemere


class EphemeralRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_analyse_ephemere(
        self, *, analyse_id: uuid.UUID, persist: bool, created_by: str
    ) -> AnalyseEphemere:
        record = AnalyseEphemere(analyse_id=analyse_id, persist=persist, created_by=created_by)
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def get_analyse_ephemere(self, analyse_id: uuid.UUID) -> AnalyseEphemere | None:
        result = await self.db.execute(select(AnalyseEphemere).where(AnalyseEphemere.analyse_id == analyse_id))
        return result.scalar_one_or_none()

    async def create_dossier_ephemere(
        self,
        *,
        dossier_id: uuid.UUID,
        analyse_ephemere_id: uuid.UUID | None,
        persist: bool,
        ttl_hours: int,
        created_by: str,
    ) -> DossierEphemere:
        record = DossierEphemere(
            dossier_id=dossier_id,
            analyse_ephemere_id=analyse_ephemere_id,
            persist=persist,
            ttl_hours=ttl_hours,
            created_by=created_by,
        )
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def get_dossier_ephemere(self, dossier_id: uuid.UUID) -> DossierEphemere | None:
        result = await self.db.execute(select(DossierEphemere).where(DossierEphemere.dossier_id == dossier_id))
        return result.scalar_one_or_none()
