"""Brouillons de document (issue #140, parent #107).

Règles portées ici :

- une version de champ n'est jamais modifiée : modifier, valider, rejeter, restaurer ou proposer en ajoute une ;
- une valeur **validée** n'est jamais réécrite par l'agent ni par une régénération : seule une personne la change ;
- à la validation d'un champ « renseigné au fil de l'instruction », la valeur est aussi écrite dans l'analyse
  comme élément de type ``field`` (versions, propositions, notes et reprise à la relance de l'analyse, #119) ;
  les champs tirés de l'analyse ne sont pas recopiés ;
- chaque décision est consignée au journal, avec le temps écoulé depuis la proposition.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import TypeAdapter
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.factory import RequestContext
from app.models.document_draft import (
    DocumentDraft,
    DocumentFieldEvent,
    DocumentFieldVersion,
    DraftStatus,
    FieldEventKind,
    FieldOrigin,
    FieldStatus,
)
from app.models.document_template import DocumentTemplate, DocumentTemplateVersion
from app.models.dossier import Dossier
from app.models.dossier_analysis import (
    AnalysisElement,
    AnalysisElementKind,
    AnalysisElementVersion,
    DossierAnalysis,
    DossierAnalysisStatus,
    ElementVersionOrigin,
)
from app.repositories.dossier_analysis_repository import DossierAnalysisRepository
from app.schemas.document_draft import (
    CompletenessOut,
    DraftFieldOut,
    DraftOut,
    DraftSummaryOut,
    FieldVersionOut,
)
from app.schemas.document_template import FieldDefinition, FieldList, InstructionSource, MetadataSource
from app.services.document_fields import coerce_value, resolve_initial_values, value_to_text


class DraftError(Exception):
    """Erreur métier sur un brouillon : le message est destiné à l'utilisateur."""


class UnknownFieldError(DraftError):
    pass


class DraftNotEditableError(DraftError):
    pass


class ValidatedFieldError(DraftError):
    """Une valeur validée à la main n'est pas réécrite automatiquement."""


class NothingToValidateError(DraftError):
    pass


def template_definitions(template_version: DocumentTemplateVersion) -> list[FieldDefinition]:
    return TypeAdapter(FieldList).validate_python({"fields": template_version.fields}).fields


def _is_generated_at(definition: FieldDefinition) -> bool:
    # Posée à l'assemblage du fichier (#143) : ne bloque pas la complétude du brouillon.
    return isinstance(definition.source, MetadataSource) and definition.source.key == "generated_at"


class DocumentDraftRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # --- Lecture ---

    async def get(self, dossier_id: uuid.UUID, draft_id: uuid.UUID) -> DocumentDraft | None:
        result = await self.db.execute(
            select(DocumentDraft)
            .where(DocumentDraft.id == draft_id, DocumentDraft.dossier_id == dossier_id)
            .execution_options(populate_existing=True)
        )
        return result.scalar_one_or_none()

    async def list_for_dossier(self, dossier_id: uuid.UUID) -> list[DraftSummaryOut]:
        rows = (
            await self.db.execute(
                select(DocumentDraft, DocumentTemplateVersion)
                .join(DocumentTemplateVersion, DocumentTemplateVersion.id == DocumentDraft.template_version_id)
                .where(DocumentDraft.dossier_id == dossier_id)
                .order_by(DocumentDraft.created_at.desc(), DocumentDraft.id)
            )
        ).all()
        return [
            DraftSummaryOut(
                id=d.id,
                dossier_id=d.dossier_id,
                template_id=d.template_id,
                template_name=v.name,
                template_version_number=v.version_number,
                status=d.status,
                created_by=d.created_by,
                created_at=d.created_at,
            )
            for d, v in rows
        ]

    async def template_version(self, draft: DocumentDraft) -> DocumentTemplateVersion:
        return await self.db.get(DocumentTemplateVersion, draft.template_version_id)

    async def current_versions(self, draft_id: uuid.UUID) -> dict[str, DocumentFieldVersion]:
        rows = await self.db.execute(
            select(DocumentFieldVersion)
            .where(DocumentFieldVersion.draft_id == draft_id)
            .order_by(DocumentFieldVersion.version_number)
            .execution_options(populate_existing=True)
        )
        return {version.field_name: version for version in rows.scalars()}

    async def field_versions(self, draft_id: uuid.UUID, name: str) -> list[DocumentFieldVersion]:
        rows = await self.db.execute(
            select(DocumentFieldVersion)
            .where(DocumentFieldVersion.draft_id == draft_id, DocumentFieldVersion.field_name == name)
            .order_by(DocumentFieldVersion.version_number)
        )
        return list(rows.scalars())

    async def events(self, draft_id: uuid.UUID, name: str | None = None) -> list[DocumentFieldEvent]:
        query = select(DocumentFieldEvent).where(DocumentFieldEvent.draft_id == draft_id)
        if name is not None:
            query = query.where(DocumentFieldEvent.field_name == name)
        rows = await self.db.execute(query.order_by(DocumentFieldEvent.seq))
        return list(rows.scalars())

    def completeness(
        self, definitions: list[FieldDefinition], current: dict[str, DocumentFieldVersion]
    ) -> CompletenessOut:
        missing, proposed = [], []
        for definition in definitions:
            if not definition.required or _is_generated_at(definition):
                continue
            status = current[definition.name].status
            if status == FieldStatus.NON_RENSEIGNE:
                missing.append(definition.name)
            elif status == FieldStatus.PROPOSE:
                proposed.append(definition.name)
        return CompletenessOut(complete=not missing and not proposed, missing=missing, proposed=proposed)

    async def build_out(self, draft: DocumentDraft) -> DraftOut:
        template_version = await self.template_version(draft)
        definitions = template_definitions(template_version)
        current = await self.current_versions(draft.id)
        return DraftOut(
            id=draft.id,
            dossier_id=draft.dossier_id,
            analysis_id=draft.analysis_id,
            revision_id=draft.revision_id,
            template_id=draft.template_id,
            template_version_id=draft.template_version_id,
            template_name=template_version.name,
            template_version_number=template_version.version_number,
            status=draft.status,
            created_by=draft.created_by,
            created_at=draft.created_at,
            fields=[
                DraftFieldOut(
                    name=d.name,
                    label=d.label,
                    type=d.type,
                    required=d.required,
                    instruction=d.instruction,
                    source=d.source.model_dump(),
                    current=FieldVersionOut.model_validate(current[d.name]),
                )
                for d in definitions
            ],
            completeness=self.completeness(definitions, current),
        )

    # --- Création ---

    async def create(
        self,
        *,
        dossier: Dossier,
        analysis: DossierAnalysis,
        revision_id: uuid.UUID,
        template: DocumentTemplate,
        user: RequestContext,
    ) -> DocumentDraft:
        template_version = template.current
        definitions = template_definitions(template_version)
        initial = await resolve_initial_values(
            self.db, dossier=dossier, revision_id=revision_id, fields=definitions, user=user
        )
        draft = DocumentDraft(
            dossier_id=dossier.id,
            analysis_id=analysis.id,
            revision_id=revision_id,
            template_id=template.id,
            template_version_id=template_version.id,
            status=DraftStatus.BROUILLON,
            created_by=user.user_id,
        )
        self.db.add(draft)
        await self.db.flush()
        for definition in definitions:
            start = initial[definition.name]
            version = DocumentFieldVersion(
                draft_id=draft.id,
                field_name=definition.name,
                version_number=1,
                value=start.value,
                status=start.status,
                origin=start.origin,
                sources=start.sources,
            )
            self.db.add(version)
            await self.db.flush()
            if start.status == FieldStatus.PROPOSE:
                self._event(draft, definition.name, FieldEventKind.PROPOSED, version, sources=start.sources)
        await self.db.commit()
        return draft

    # --- Écritures ---

    def _check_editable(self, draft: DocumentDraft) -> None:
        if draft.status != DraftStatus.BROUILLON:
            raise DraftNotEditableError("Ce brouillon n'est plus modifiable")

    async def _lock(self, draft: DocumentDraft) -> None:
        """Sérialise les écritures sur un brouillon (numéros de version, règle « jamais réécrit »)."""
        await self.db.execute(select(DocumentDraft.id).where(DocumentDraft.id == draft.id).with_for_update())
        await self.db.refresh(draft)

    async def _current(self, draft: DocumentDraft, name: str) -> DocumentFieldVersion:
        versions = await self.field_versions(draft.id, name)
        if not versions:
            raise UnknownFieldError(f"Champ inconnu : {name}")
        return versions[-1]

    async def _append(
        self,
        draft: DocumentDraft,
        name: str,
        *,
        value: Any | None,
        status: FieldStatus,
        origin: FieldOrigin,
        sources: list[dict[str, Any]],
        author_id: str | None = None,
        reason: str | None = None,
        restored_from: uuid.UUID | None = None,
        prompt_version: str | None = None,
        model: str | None = None,
    ) -> DocumentFieldVersion:
        number = (
            await self.db.execute(
                select(func.coalesce(func.max(DocumentFieldVersion.version_number), 0)).where(
                    DocumentFieldVersion.draft_id == draft.id, DocumentFieldVersion.field_name == name
                )
            )
        ).scalar_one() + 1
        version = DocumentFieldVersion(
            draft_id=draft.id,
            field_name=name,
            version_number=number,
            value=value,
            status=status,
            origin=origin,
            sources=sources,
            author_id=author_id,
            reason=reason,
            restored_from_version_id=restored_from,
            prompt_version=prompt_version,
            model=model,
        )
        self.db.add(version)
        await self.db.flush()
        return version

    def _event(
        self,
        draft: DocumentDraft,
        name: str,
        kind: FieldEventKind,
        version: DocumentFieldVersion,
        *,
        author_id: str | None = None,
        duration: float | None = None,
        detail: str | None = None,
        sources: list[dict[str, Any]] | None = None,
    ) -> None:
        self.db.add(
            DocumentFieldEvent(
                draft_id=draft.id,
                field_name=name,
                kind=kind,
                version_id=version.id,
                author_id=author_id,
                duration_seconds=duration,
                prompt_version=version.prompt_version,
                model=version.model,
                sources=version.sources if sources is None else sources,
                detail=detail,
            )
        )

    async def _decision_duration(self, draft: DocumentDraft, name: str, current: DocumentFieldVersion) -> float | None:
        """Temps écoulé depuis la proposition que la décision tranche (aucune si rien n'était proposé)."""
        if current.status != FieldStatus.PROPOSE:
            return None
        proposed_at = (
            await self.db.execute(
                select(func.max(DocumentFieldEvent.created_at)).where(
                    DocumentFieldEvent.draft_id == draft.id,
                    DocumentFieldEvent.field_name == name,
                    DocumentFieldEvent.kind.in_([FieldEventKind.PROPOSED, FieldEventKind.REGENERATED]),
                )
            )
        ).scalar_one()
        return (datetime.now(UTC) - proposed_at).total_seconds() if proposed_at else None

    async def _write_back(
        self, draft: DocumentDraft, definition: FieldDefinition, value: Any, user_id: str, template_name: str
    ) -> str | None:
        """Recopie dans l'analyse un champ « renseigné au fil de l'instruction » validé. Renvoie une précision
        pour le journal, ou None quand le champ n'est pas concerné."""
        if not isinstance(definition.source, InstructionSource):
            return None
        analysis = await self.db.get(DossierAnalysis, draft.analysis_id)
        if analysis is None or analysis.status == DossierAnalysisStatus.FIGEE:
            return "Analyse figée : valeur non recopiée dans l'analyse"
        text = value_to_text(value)
        repository = DossierAnalysisRepository(self.db)
        element = (
            await self.db.execute(
                select(AnalysisElement)
                .where(
                    AnalysisElement.analysis_id == analysis.id,
                    AnalysisElement.kind == AnalysisElementKind.FIELD,
                    AnalysisElement.definition_name == definition.name,
                )
                .order_by(AnalysisElement.created_at)
                .limit(1)
            )
        ).scalar_one_or_none()
        reason = f"Champ « {definition.label} » du document « {template_name} »"
        if element is None:
            created = await repository.create_element(
                analysis,
                kind=AnalysisElementKind.FIELD,
                value={"value": text},
                origin=ElementVersionOrigin.INSTRUCTOR,
                definition_name=definition.name,
                author_id=user_id,
                reason=reason,
                source_type="document_draft",
                source_id=draft.id,
                commit=False,
            )
            return f"Recopié dans l'analyse (élément {created.id})"
        retained = await self.db.get(AnalysisElementVersion, element.retained_version_id)
        if retained is not None and retained.value.get("value") == text:
            return f"Déjà dans l'analyse (élément {element.id})"
        await repository.add_version(
            element,
            value={"value": text},
            origin=ElementVersionOrigin.INSTRUCTOR,
            author_id=user_id,
            reason=reason,
            source_type="document_draft",
            source_id=draft.id,
            commit=False,
        )
        return f"Recopié dans l'analyse (élément {element.id})"

    async def set_value(
        self, draft: DocumentDraft, definition: FieldDefinition, raw: Any, *, user_id: str, reason: str | None
    ) -> DocumentFieldVersion:
        """Saisie à la main : la valeur est validée d'office."""
        value = coerce_value(definition.type, raw)
        await self._lock(draft)
        self._check_editable(draft)
        current = await self._current(draft, definition.name)
        accepted = current.status == FieldStatus.PROPOSE and current.value == value
        duration = await self._decision_duration(draft, definition.name, current)
        version = await self._append(
            draft,
            definition.name,
            value=value,
            status=FieldStatus.VALIDE,
            origin=current.origin if accepted else FieldOrigin.INSTRUCTOR,
            sources=current.sources if accepted else [],
            author_id=user_id,
            reason=reason,
        )
        template_name = (await self.template_version(draft)).name
        detail = await self._write_back(draft, definition, value, user_id, template_name)
        self._event(
            draft,
            definition.name,
            FieldEventKind.ACCEPTED if accepted else FieldEventKind.MODIFIED,
            version,
            author_id=user_id,
            duration=duration,
            detail=detail if reason is None else (f"{reason} — {detail}" if detail else reason),
        )
        await self.db.commit()
        return version

    async def _validate_one(
        self, draft: DocumentDraft, definition: FieldDefinition, template_name: str, user_id: str
    ) -> DocumentFieldVersion:
        current = await self._current(draft, definition.name)
        if current.status != FieldStatus.PROPOSE or current.value is None:
            raise NothingToValidateError(f"« {definition.label} » n'a pas de valeur proposée à valider")
        duration = await self._decision_duration(draft, definition.name, current)
        version = await self._append(
            draft,
            definition.name,
            value=current.value,
            status=FieldStatus.VALIDE,
            origin=current.origin,
            sources=current.sources,
            author_id=user_id,
            prompt_version=current.prompt_version,
            model=current.model,
        )
        detail = await self._write_back(draft, definition, current.value, user_id, template_name)
        self._event(
            draft,
            definition.name,
            FieldEventKind.ACCEPTED,
            version,
            author_id=user_id,
            duration=duration,
            detail=detail,
        )
        return version

    async def validate(
        self, draft: DocumentDraft, definition: FieldDefinition, *, user_id: str
    ) -> DocumentFieldVersion:
        """Accepte la valeur proposée telle quelle."""
        await self._lock(draft)
        self._check_editable(draft)
        template_name = (await self.template_version(draft)).name
        version = await self._validate_one(draft, definition, template_name, user_id)
        await self.db.commit()
        return version

    async def validate_many(
        self, draft: DocumentDraft, definitions: list[FieldDefinition], names: list[str] | None, *, user_id: str
    ) -> list[DocumentFieldVersion]:
        """Accepte d'un coup les valeurs proposées (celles données, ou toutes) ; tout ou rien."""
        await self._lock(draft)
        self._check_editable(draft)
        template_name = (await self.template_version(draft)).name
        current = await self.current_versions(draft.id)
        by_name = {d.name: d for d in definitions}
        if names is not None:
            unknown = [n for n in names if n not in by_name]
            if unknown:
                raise UnknownFieldError(f"Champ inconnu : {', '.join(unknown)}")
            targets = [by_name[n] for n in names]
        else:
            targets = [d for d in definitions if current[d.name].status == FieldStatus.PROPOSE]
        versions = [await self._validate_one(draft, d, template_name, user_id) for d in targets]
        await self.db.commit()
        return versions

    async def reject(
        self, draft: DocumentDraft, definition: FieldDefinition, *, user_id: str, reason: str | None
    ) -> DocumentFieldVersion:
        """Écarte la valeur proposée : le champ redevient « non renseigné »."""
        await self._lock(draft)
        self._check_editable(draft)
        current = await self._current(draft, definition.name)
        if current.status != FieldStatus.PROPOSE:
            raise NothingToValidateError(f"« {definition.label} » n'a pas de valeur proposée à rejeter")
        duration = await self._decision_duration(draft, definition.name, current)
        version = await self._append(
            draft,
            definition.name,
            value=None,
            status=FieldStatus.NON_RENSEIGNE,
            origin=current.origin,
            sources=[],
            author_id=user_id,
            reason=reason,
        )
        self._event(
            draft,
            definition.name,
            FieldEventKind.REJECTED,
            version,
            author_id=user_id,
            duration=duration,
            detail=reason,
        )
        await self.db.commit()
        return version

    async def restore(
        self, draft: DocumentDraft, definition: FieldDefinition, version_id: uuid.UUID, *, user_id: str
    ) -> DocumentFieldVersion:
        """Reprend la valeur d'une version antérieure du champ (validée d'office : décision de la personne)."""
        await self._lock(draft)
        self._check_editable(draft)
        target = next((v for v in await self.field_versions(draft.id, definition.name) if v.id == version_id), None)
        if target is None:
            raise UnknownFieldError("Version introuvable pour ce champ")
        if target.value is None:
            raise DraftError("Cette version n'a pas de valeur à restaurer")
        current = await self._current(draft, definition.name)
        duration = await self._decision_duration(draft, definition.name, current)
        version = await self._append(
            draft,
            definition.name,
            value=target.value,
            status=FieldStatus.VALIDE,
            origin=FieldOrigin.INSTRUCTOR,
            sources=target.sources,
            author_id=user_id,
            restored_from=target.id,
        )
        template_name = (await self.template_version(draft)).name
        detail = await self._write_back(draft, definition, target.value, user_id, template_name)
        self._event(
            draft,
            definition.name,
            FieldEventKind.RESTORED,
            version,
            author_id=user_id,
            duration=duration,
            detail=detail,
        )
        await self.db.commit()
        return version

    async def propose(
        self,
        draft: DocumentDraft,
        definition: FieldDefinition,
        raw: Any,
        *,
        sources: list[dict[str, Any]],
        prompt_version: str | None,
        model: str | None,
        instruction: str | None = None,
    ) -> DocumentFieldVersion:
        """Proposition de l'agent de génération (#141). Une valeur validée n'est jamais réécrite."""
        value = coerce_value(definition.type, raw)
        await self._lock(draft)
        self._check_editable(draft)
        current = await self._current(draft, definition.name)
        if current.status == FieldStatus.VALIDE:
            raise ValidatedFieldError(f"« {definition.label} » est validé : il ne se réécrit pas automatiquement")
        version = await self._append(
            draft,
            definition.name,
            value=value,
            status=FieldStatus.PROPOSE,
            origin=FieldOrigin.AGENT,
            sources=sources,
            prompt_version=prompt_version,
            model=model,
        )
        regenerated = instruction is not None or current.status == FieldStatus.PROPOSE
        self._event(
            draft,
            definition.name,
            FieldEventKind.REGENERATED if regenerated else FieldEventKind.PROPOSED,
            version,
            detail=instruction,
        )
        await self.db.commit()
        return version

    async def set_status(self, draft: DocumentDraft, status: DraftStatus) -> DocumentDraft:
        draft.status = status
        await self.db.commit()
        return draft
