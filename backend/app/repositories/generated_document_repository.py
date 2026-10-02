"""Documents générés à partir d'un brouillon (issue #143, parent #107).

Un document est le résultat figé d'un assemblage ; régénérer en ajoute un, l'ancien reste. Interne : la
visibilité est « interne » dès la première version (#105 pourra l'ouvrir)."""

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_draft import DocumentDraft
from app.models.generated_document import VISIBILITY_INTERNAL, GeneratedDocument
from app.schemas.generated_document import GeneratedDocumentOut


def document_out(document: GeneratedDocument) -> GeneratedDocumentOut:
    return GeneratedDocumentOut(
        id=document.id,
        dossier_id=document.dossier_id,
        draft_id=document.draft_id,
        version_number=document.version_number,
        template_id=document.template_id,
        template_name=document.template_name,
        template_version_number=document.template_version_number,
        analysis_id=document.analysis_id,
        revision_id=document.revision_id,
        revision_number=document.revision_number,
        file_name=document.file_name,
        has_pdf=document.pdf_key is not None,
        odt_size=document.odt_size,
        pdf_size=document.pdf_size,
        incomplete_fields=document.incomplete_fields,
        visibility=document.visibility,
        author_id=document.author_id,
        created_at=document.created_at,
        values=document.values,
    )


class GeneratedDocumentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_for_dossier(
        self, dossier_id: uuid.UUID, draft_id: uuid.UUID | None = None
    ) -> list[GeneratedDocument]:
        query = select(GeneratedDocument).where(GeneratedDocument.dossier_id == dossier_id)
        if draft_id is not None:
            query = query.where(GeneratedDocument.draft_id == draft_id)
        rows = await self.db.execute(query.order_by(GeneratedDocument.created_at.desc(), GeneratedDocument.id))
        return list(rows.scalars())

    async def get(self, dossier_id: uuid.UUID, document_id: uuid.UUID) -> GeneratedDocument | None:
        row = await self.db.execute(
            select(GeneratedDocument).where(
                GeneratedDocument.id == document_id, GeneratedDocument.dossier_id == dossier_id
            )
        )
        return row.scalar_one_or_none()

    async def next_version_number(self, draft: DocumentDraft) -> int:
        """Numéro de la prochaine version du brouillon. À appeler après avoir verrouillé le brouillon."""
        return (
            await self.db.execute(
                select(func.coalesce(func.max(GeneratedDocument.version_number), 0)).where(
                    GeneratedDocument.draft_id == draft.id
                )
            )
        ).scalar_one() + 1

    async def lock_draft(self, draft: DocumentDraft) -> None:
        """Sérialise les générations d'un même brouillon (numéros de version distincts)."""
        await self.db.execute(select(DocumentDraft.id).where(DocumentDraft.id == draft.id).with_for_update())

    async def add(self, **fields: Any) -> GeneratedDocument:
        document = GeneratedDocument(visibility=VISIBILITY_INTERNAL, **fields)
        self.db.add(document)
        await self.db.commit()
        return document
