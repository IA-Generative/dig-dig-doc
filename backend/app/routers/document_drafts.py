"""Routes des brouillons de document d'un dossier (issue #140, parent #107).

Réservées aux utilisateurs authentifiés : un brouillon est **interne**, jamais exposé côté usager (#96).
Un brouillon lie un modèle (version précise) à une révision de l'analyse du dossier ; ses champs ont chacun
un état (non renseigné, proposé, validé), des versions en ajout seul et un journal des décisions."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.factory import RequestContext, get_current_user
from app.db import get_db
from app.models.document_draft import DocumentDraft, DraftStatus
from app.models.dossier_analysis import AnalysisRevision, DossierAnalysis
from app.repositories.document_draft_repository import (
    DocumentDraftRepository,
    DraftError,
    DraftNotEditableError,
    NothingToValidateError,
    UnknownFieldError,
    ValidatedFieldError,
    template_definitions,
)
from app.repositories.document_template_repository import DocumentTemplateRepository
from app.repositories.dossier_analysis_repository import DossierAnalysisRepository
from app.repositories.dossier_repository import DossierRepository
from app.schemas.document_draft import (
    CompletenessOut,
    DraftCreateIn,
    DraftOut,
    DraftSummaryOut,
    FieldEventOut,
    FieldRejectIn,
    FieldRestoreIn,
    FieldsValidateIn,
    FieldValueIn,
    FieldVersionOut,
)
from app.schemas.document_template import FieldDefinition
from app.services.document_fields import FieldValueError

router = APIRouter(prefix="/dossiers", tags=["Documents"], dependencies=[Depends(get_current_user)])


def _error(error: Exception) -> HTTPException:
    if isinstance(error, UnknownFieldError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, DraftNotEditableError | ValidatedFieldError | NothingToValidateError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error))


async def _draft_or_404(db: AsyncSession, dossier_id: uuid.UUID, draft_id: uuid.UUID) -> DocumentDraft:
    if await DossierRepository(db).get(dossier_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dossier introuvable")
    draft = await DocumentDraftRepository(db).get(dossier_id, draft_id)
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brouillon introuvable")
    return draft


async def _definition(db: AsyncSession, draft: DocumentDraft, name: str) -> FieldDefinition:
    template_version = await DocumentDraftRepository(db).template_version(draft)
    definition = next((d for d in template_definitions(template_version) if d.name == name), None)
    if definition is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Champ inconnu : {name}")
    return definition


@router.get("/{dossier_id}/document-drafts", response_model=list[DraftSummaryOut])
async def list_drafts(dossier_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]):
    if await DossierRepository(db).get(dossier_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dossier introuvable")
    return await DocumentDraftRepository(db).list_for_dossier(dossier_id)


@router.post("/{dossier_id}/document-drafts", response_model=DraftOut, status_code=status.HTTP_201_CREATED)
async def create_draft(
    dossier_id: uuid.UUID,
    body: DraftCreateIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
):
    """Crée un brouillon : un modèle (sa version actuelle) pour ce dossier. Sans ``revision_id``, un instantané
    de l'analyse courante est pris ; sinon la révision donnée (d'une analyse du dossier) est utilisée."""
    dossier = await DossierRepository(db).get(dossier_id)
    if dossier is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dossier introuvable")
    template = await DocumentTemplateRepository(db).get(body.template_id)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Modèle introuvable")
    if template.archived:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ce modèle est archivé")

    analyses = DossierAnalysisRepository(db)
    if body.revision_id is None:
        analysis = await analyses.get_current(dossier_id)
        if analysis is None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ce dossier n'a pas encore d'analyse")
        revision, _ = await analyses.create_revision(
            analysis, author_id=user.user_id, label=f"Document : {template.current.name}"
        )
    else:
        revision = await db.get(AnalysisRevision, body.revision_id)
        analysis = await db.get(DossierAnalysis, revision.analysis_id) if revision else None
        if analysis is None or analysis.dossier_id != dossier_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Révision introuvable pour ce dossier")
    draft = await DocumentDraftRepository(db).create(
        dossier=dossier, analysis=analysis, revision_id=revision.id, template=template, user=user
    )
    return await DocumentDraftRepository(db).build_out(draft)


@router.get("/{dossier_id}/document-drafts/{draft_id}", response_model=DraftOut)
async def get_draft(dossier_id: uuid.UUID, draft_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]):
    draft = await _draft_or_404(db, dossier_id, draft_id)
    return await DocumentDraftRepository(db).build_out(draft)


@router.get("/{dossier_id}/document-drafts/{draft_id}/completeness", response_model=CompletenessOut)
async def get_completeness(dossier_id: uuid.UUID, draft_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]):
    """Champs obligatoires pas encore validés : à renseigner, ou seulement proposés."""
    draft = await _draft_or_404(db, dossier_id, draft_id)
    repository = DocumentDraftRepository(db)
    definitions = template_definitions(await repository.template_version(draft))
    return repository.completeness(definitions, await repository.current_versions(draft.id))


@router.post("/{dossier_id}/document-drafts/{draft_id}/archive", response_model=DraftOut)
async def archive_draft(dossier_id: uuid.UUID, draft_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]):
    draft = await _draft_or_404(db, dossier_id, draft_id)
    repository = DocumentDraftRepository(db)
    await repository.set_status(draft, DraftStatus.ARCHIVE)
    return await repository.build_out(draft)


@router.put("/{dossier_id}/document-drafts/{draft_id}/fields/{name}", response_model=FieldVersionOut)
async def set_field_value(
    dossier_id: uuid.UUID,
    draft_id: uuid.UUID,
    name: str,
    body: FieldValueIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
):
    """Saisie à la main : ajoute une version, validée d'office. Pour un champ « renseigné au fil de
    l'instruction », la valeur est aussi écrite dans l'analyse."""
    draft = await _draft_or_404(db, dossier_id, draft_id)
    definition = await _definition(db, draft, name)
    try:
        return await DocumentDraftRepository(db).set_value(
            draft, definition, body.value, user_id=user.user_id, reason=body.reason
        )
    except (DraftError, FieldValueError) as error:
        raise _error(error) from error


@router.post("/{dossier_id}/document-drafts/{draft_id}/fields/{name}/validate", response_model=FieldVersionOut)
async def validate_field(
    dossier_id: uuid.UUID,
    draft_id: uuid.UUID,
    name: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
):
    """Accepte la valeur proposée telle quelle."""
    draft = await _draft_or_404(db, dossier_id, draft_id)
    definition = await _definition(db, draft, name)
    try:
        return await DocumentDraftRepository(db).validate(draft, definition, user_id=user.user_id)
    except DraftError as error:
        raise _error(error) from error


@router.post("/{dossier_id}/document-drafts/{draft_id}/fields/{name}/reject", response_model=FieldVersionOut)
async def reject_field(
    dossier_id: uuid.UUID,
    draft_id: uuid.UUID,
    name: str,
    body: FieldRejectIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
):
    """Écarte la valeur proposée : le champ redevient « non renseigné »."""
    draft = await _draft_or_404(db, dossier_id, draft_id)
    definition = await _definition(db, draft, name)
    try:
        return await DocumentDraftRepository(db).reject(draft, definition, user_id=user.user_id, reason=body.reason)
    except DraftError as error:
        raise _error(error) from error


@router.post("/{dossier_id}/document-drafts/{draft_id}/validate", response_model=list[FieldVersionOut])
async def validate_fields(
    dossier_id: uuid.UUID,
    draft_id: uuid.UUID,
    body: FieldsValidateIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
):
    """Accepte d'un coup les valeurs proposées (celles données, ou toutes). Tout ou rien."""
    draft = await _draft_or_404(db, dossier_id, draft_id)
    repository = DocumentDraftRepository(db)
    definitions = template_definitions(await repository.template_version(draft))
    try:
        return await repository.validate_many(draft, definitions, body.names, user_id=user.user_id)
    except DraftError as error:
        raise _error(error) from error


@router.get("/{dossier_id}/document-drafts/{draft_id}/fields/{name}/versions", response_model=list[FieldVersionOut])
async def list_field_versions(
    dossier_id: uuid.UUID, draft_id: uuid.UUID, name: str, db: Annotated[AsyncSession, Depends(get_db)]
):
    draft = await _draft_or_404(db, dossier_id, draft_id)
    await _definition(db, draft, name)
    return await DocumentDraftRepository(db).field_versions(draft.id, name)


@router.post("/{dossier_id}/document-drafts/{draft_id}/fields/{name}/restore", response_model=FieldVersionOut)
async def restore_field_version(
    dossier_id: uuid.UUID,
    draft_id: uuid.UUID,
    name: str,
    body: FieldRestoreIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
):
    """Reprend la valeur d'une version antérieure : ajoute une version, rien n'est écrasé."""
    draft = await _draft_or_404(db, dossier_id, draft_id)
    definition = await _definition(db, draft, name)
    try:
        return await DocumentDraftRepository(db).restore(draft, definition, body.version_id, user_id=user.user_id)
    except DraftError as error:
        raise _error(error) from error


@router.get("/{dossier_id}/document-drafts/{draft_id}/events", response_model=list[FieldEventOut])
async def list_events(
    dossier_id: uuid.UUID,
    draft_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    field: Annotated[str | None, Query()] = None,
):
    """Journal des décisions (interne), du plus ancien au plus récent ; ``field`` filtre sur un champ."""
    draft = await _draft_or_404(db, dossier_id, draft_id)
    return await DocumentDraftRepository(db).events(draft.id, field)
