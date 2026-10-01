"""Notes internes d'un dossier (issue #117).

Règles portées ici : une version n'est jamais modifiée (modifier ou restaurer
en ajoute une) ; « supprimer » archive ; l'analyse d'une note par le worker est
suivie sur la note (une seule à la fois)."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.dossier_note import (
    NOTE_ANALYSIS_DONE,
    NOTE_ANALYSIS_FAILED,
    NOTE_ANALYSIS_RUNNING,
    DossierNote,
    DossierNoteVersion,
)
from app.schemas.dossier_note import NoteOut


class NoteArchivedError(Exception):
    """Une note archivée ne se modifie pas : il faut d'abord la restaurer."""


class NoteAnalysisRunningError(Exception):
    """L'analyse de cette note est déjà en cours."""


def note_out(note: DossierNote) -> NoteOut:
    current = note.current
    return NoteOut(
        id=note.id,
        dossier_id=note.dossier_id,
        created_by=note.created_by,
        archived=note.archived,
        content=current.content,
        version_number=current.version_number,
        last_author_id=current.author_id,
        created_at=note.created_at,
        updated_at=current.created_at,
        analysis_status=note.analysis_status,
        analysis_version_number=note.analysis_version_number,
        analysis_proposal_count=note.analysis_proposal_count,
        analysis_error=note.analysis_error,
    )


class DossierNoteRepository:
    def __init__(self, db) -> None:
        self.db = db

    def _query(self):
        # populate_existing : la session garde les objets (expire_on_commit=False),
        # sans cela une note déjà chargée garderait son ancienne liste de versions.
        return select(DossierNote).options(selectinload(DossierNote.versions)).execution_options(populate_existing=True)

    async def list(self, dossier_id: uuid.UUID, *, include_archived: bool = False) -> list[DossierNote]:
        query = self._query().where(DossierNote.dossier_id == dossier_id)
        if not include_archived:
            query = query.where(DossierNote.archived.is_(False))
        result = await self.db.execute(query.order_by(DossierNote.created_at.desc(), DossierNote.id))
        return list(result.scalars().all())

    async def get(self, dossier_id: uuid.UUID, note_id: uuid.UUID) -> DossierNote | None:
        result = await self.db.execute(
            self._query().where(DossierNote.id == note_id, DossierNote.dossier_id == dossier_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, note_id: uuid.UUID) -> DossierNote | None:
        result = await self.db.execute(self._query().where(DossierNote.id == note_id))
        return result.scalar_one_or_none()

    async def create(self, dossier_id: uuid.UUID, *, content: str, user_id: str) -> DossierNote:
        note = DossierNote(dossier_id=dossier_id, created_by=user_id)
        note.versions = [DossierNoteVersion(version_number=1, content=content, author_id=user_id)]
        self.db.add(note)
        await self.db.commit()
        return await self.get(dossier_id, note.id)

    async def add_version(
        self, note: DossierNote, *, content: str, user_id: str, restored_from: uuid.UUID | None = None
    ) -> DossierNote:
        """Ajoute une version (modification ou restauration). Une note archivée
        ne se modifie pas."""
        if note.archived:
            raise NoteArchivedError()
        self.db.add(
            DossierNoteVersion(
                note_id=note.id,
                version_number=note.current.version_number + 1,
                content=content,
                author_id=user_id,
                restored_from_version_id=restored_from,
            )
        )
        await self.db.commit()
        return await self.get(note.dossier_id, note.id)

    async def set_archived(self, note: DossierNote, archived: bool) -> DossierNote:
        note.archived = archived
        await self.db.commit()
        return await self.get(note.dossier_id, note.id)

    # --- Analyse par le worker ---

    async def start_analysis(self, note: DossierNote, *, user_id: str) -> DossierNote:
        """Marque la note « en cours d'analyse » pour la version actuelle. Une
        seule analyse à la fois par note."""
        if note.analysis_status == NOTE_ANALYSIS_RUNNING:
            raise NoteAnalysisRunningError()
        note.analysis_status = NOTE_ANALYSIS_RUNNING
        note.analysis_requested_by = user_id
        note.analysis_requested_at = datetime.now(UTC)
        note.analysis_version_number = note.current.version_number
        note.analysis_proposal_count = None
        note.analysis_error = None
        await self.db.commit()
        return await self.get(note.dossier_id, note.id)

    async def finish_analysis(
        self, note: DossierNote, *, status: str, proposal_count: int | None, error: str | None
    ) -> DossierNote:
        note.analysis_status = NOTE_ANALYSIS_DONE if status == NOTE_ANALYSIS_DONE else NOTE_ANALYSIS_FAILED
        note.analysis_proposal_count = proposal_count
        note.analysis_error = error
        await self.db.commit()
        return await self.get(note.dossier_id, note.id)
