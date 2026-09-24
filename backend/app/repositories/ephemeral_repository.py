import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analyse_ephemere import AnalyseEphemere


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
