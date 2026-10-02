"""Modèles de document (issue #138).

Règles portées ici : une version n'est jamais modifiée (modifier ou restaurer en ajoute une) ;
« supprimer » archive ; deux modèles ne portent pas le même nom (casse ignorée)."""

import uuid
from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.document_template import DocumentTemplate, DocumentTemplateVersion
from app.schemas.document_template import FieldDefinition, PlaceholderReport, TemplateOut


class TemplateArchivedError(Exception):
    """Un modèle archivé ne se modifie pas : il faut d'abord le désarchiver."""


class TemplateNameTakenError(Exception):
    """Un autre modèle porte déjà ce nom."""


def placeholder_report(placeholders: list[str], fields: list[FieldDefinition]) -> PlaceholderReport:
    """Tout placeholder doit avoir un champ défini, et tout champ défini doit être dans le fichier."""
    names = {field.name for field in fields}
    found = set(placeholders)
    return PlaceholderReport(unknown_placeholders=sorted(found - names), unused_fields=sorted(names - found))


def template_out(template: DocumentTemplate) -> TemplateOut:
    current = template.current
    return TemplateOut(
        id=template.id,
        analyse_id=template.analyse_id,
        archived=template.archived,
        created_by=template.created_by,
        created_at=template.created_at,
        updated_at=current.created_at,
        version_number=current.version_number,
        name=current.name,
        description=current.description,
        generation_instructions=current.generation_instructions,
        fields=current.fields,
        placeholders=current.placeholders,
        warnings=current.warnings,
        file_name=current.file_name,
        file_size=current.file_size,
        last_author_id=current.author_id,
    )


class DocumentTemplateRepository:
    def __init__(self, db) -> None:
        self.db = db

    def _query(self):
        # populate_existing : la session garde les objets (expire_on_commit=False), sans cela un modèle
        # déjà chargé garderait son ancienne liste de versions.
        return (
            select(DocumentTemplate)
            .options(selectinload(DocumentTemplate.versions))
            .execution_options(populate_existing=True)
        )

    async def list_all(
        self, *, analyse_id: uuid.UUID | None = None, include_archived: bool = False
    ) -> list[DocumentTemplate]:
        """Modèles, tous ou ceux d'une analyse (les plus récents d'abord)."""
        query = self._query()
        if analyse_id is not None:
            query = query.where(DocumentTemplate.analyse_id == analyse_id)
        if not include_archived:
            query = query.where(DocumentTemplate.archived.is_(False))
        result = await self.db.execute(query.order_by(DocumentTemplate.created_at.desc(), DocumentTemplate.id))
        return list(result.scalars().all())

    async def get(self, template_id: uuid.UUID) -> DocumentTemplate | None:
        result = await self.db.execute(self._query().where(DocumentTemplate.id == template_id))
        return result.scalar_one_or_none()

    async def _check_name(self, name: str, *, analyse_id: uuid.UUID | None, except_id: uuid.UUID | None = None) -> None:
        """Le nom est unique **dans l'analyse** (casse ignorée) : deux analyses peuvent avoir un « Courrier »."""
        for template in await self.list_all(analyse_id=analyse_id, include_archived=True):
            if template.id != except_id and template.current.name.casefold() == name.casefold():
                raise TemplateNameTakenError(name)

    async def create(
        self,
        *,
        user_id: str,
        analyse_id: uuid.UUID,
        name: str,
        description: str,
        generation_instructions: str,
        fields: list[FieldDefinition],
        placeholders: list[str],
        warnings: list[dict],
        file_key_for: Callable[[uuid.UUID], str],
        file_name: str,
        file_size: int,
    ) -> DocumentTemplate:
        """``file_key_for(template_id)`` donne la clé S3 du fichier (elle contient l'identifiant du modèle)."""
        await self._check_name(name, analyse_id=analyse_id)
        template = DocumentTemplate(id=uuid.uuid4(), analyse_id=analyse_id, created_by=user_id)
        template.versions = [
            DocumentTemplateVersion(
                version_number=1,
                name=name,
                description=description,
                generation_instructions=generation_instructions,
                fields=[field.model_dump() for field in fields],
                placeholders=placeholders,
                warnings=warnings,
                file_key=file_key_for(template.id),
                file_name=file_name,
                file_size=file_size,
                author_id=user_id,
            )
        ]
        self.db.add(template)
        await self.db.commit()
        return await self.get(template.id)

    async def add_version(
        self,
        template: DocumentTemplate,
        *,
        user_id: str,
        name: str,
        description: str,
        generation_instructions: str,
        fields: list[FieldDefinition],
        placeholders: list[str],
        warnings: list[dict],
        file_key: str,
        file_name: str,
        file_size: int,
        restored_from: uuid.UUID | None = None,
    ) -> DocumentTemplate:
        if template.archived:
            raise TemplateArchivedError()
        await self._check_name(name, analyse_id=template.analyse_id, except_id=template.id)
        self.db.add(
            DocumentTemplateVersion(
                template_id=template.id,
                version_number=template.current.version_number + 1,
                name=name,
                description=description,
                generation_instructions=generation_instructions,
                fields=[field.model_dump() for field in fields],
                placeholders=placeholders,
                warnings=warnings,
                file_key=file_key,
                file_name=file_name,
                file_size=file_size,
                author_id=user_id,
                restored_from_version_id=restored_from,
            )
        )
        await self.db.commit()
        return await self.get(template.id)

    async def set_archived(self, template: DocumentTemplate, archived: bool) -> DocumentTemplate:
        template.archived = archived
        await self.db.commit()
        return await self.get(template.id)
