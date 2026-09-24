import uuid
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analyse_ephemere import AnalyseEphemere
from app.models.dossier import Dossier
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

    async def mark_dossier_terminal(self, dossier: Dossier) -> None:
        """Pose dossier_ephemere.expires_at (et la propage à
        analyse_ephemere, si le run référence une analyse elle-même
        éphémère) au premier passage du Dossier à un état terminal - voir
        docs/ephemeral-api.md, section "Principe du TTL". No-op si le
        dossier n'est pas éphémère, si persist=True, si expires_at est déjà
        posé (idempotent : jamais recalculé une fois figé) ou si le dossier
        n'a en fait pas de ended_at (pas encore terminal)."""
        if dossier.ended_at is None:
            return
        record = await self.get_dossier_ephemere(dossier.id)
        if record is None or record.persist or record.expires_at is not None:
            return
        record.expires_at = dossier.ended_at + timedelta(hours=record.ttl_hours)
        if record.analyse_ephemere_id is not None:
            analyse_ephemere = await self.db.get(AnalyseEphemere, record.analyse_ephemere_id)
            if analyse_ephemere is not None and not analyse_ephemere.persist:
                analyse_ephemere.last_run_ended_at = dossier.ended_at
                analyse_ephemere.expires_at = dossier.ended_at + timedelta(hours=record.ttl_hours)
        await self.db.commit()
