"""Routes des documents générés (issue #143, parent #107).

Réservées aux utilisateurs authentifiés : un document est **interne**, jamais exposé côté usager (#96). Le
fichier est assemblé de façon déterministe par le worker ``document_render`` (#146) à partir des valeurs
**validées** du brouillon, jamais par le LLM. Régénérer ajoute une version, l'ancienne reste."""

import asyncio
import re
import uuid
from datetime import UTC, datetime
from typing import Annotated, Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.celery_client import RenderFailedError, RenderWorkerUnavailableError, render_document
from app.connectors import s3_connector
from app.core.dossier_guard import require_dossier_visible
from app.core.security.factory import RequestContext, get_current_user
from app.db import get_db
from app.models.document_draft import DraftStatus
from app.models.dossier_analysis import AnalysisRevision
from app.models.dossier_event import DossierEventType
from app.repositories.document_draft_repository import (
    DocumentDraftRepository,
    generation_in_progress,
    template_definitions,
)
from app.repositories.dossier_event_repository import DossierEventRepository
from app.repositories.dossier_repository import DossierRepository
from app.repositories.generated_document_repository import GeneratedDocumentRepository, document_out
from app.schemas.generated_document import GeneratedDocumentOut, GenerateDocumentIn
from app.services.document_assembly import build_values

ODT_TYPE = "application/vnd.oasis.opendocument.text"
PDF_TYPE = "application/pdf"

router = APIRouter(
    prefix="/dossiers",
    tags=["Documents générés"],
    dependencies=[Depends(get_current_user), Depends(require_dossier_visible)],
)


async def _dossier_or_404(db: AsyncSession, dossier_id: uuid.UUID) -> None:
    if await DossierRepository(db).get(dossier_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dossier introuvable")


def _file_name(template_name: str, version_number: int) -> str:
    """Nom de fichier sûr : lettres (accents compris), chiffres, tirets."""
    base = re.sub(r"[^\w]+", "-", template_name, flags=re.UNICODE).strip("-") or "document"
    return f"{base}-v{version_number}"


async def _size(key: str) -> int | None:
    try:
        head = await asyncio.to_thread(s3_connector.client.head_object, Bucket=s3_connector.bucket, Key=key)
        return head["ContentLength"]
    except Exception:  # noqa: BLE001 - la taille est une information d'affichage
        return None


async def _discard(*keys: str | None) -> None:
    for key in keys:
        if key:
            await asyncio.to_thread(s3_connector.delete, key)


@router.post(
    "/{dossier_id}/document-drafts/{draft_id}/documents",
    response_model=GeneratedDocumentOut,
    status_code=status.HTTP_201_CREATED,
)
async def generate_document(
    dossier_id: uuid.UUID,
    draft_id: uuid.UUID,
    body: GenerateDocumentIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
):
    """Assemble le document (ODT et PDF) depuis les valeurs **validées** du brouillon et le modèle. Un champ
    obligatoire non validé refuse la génération (409, avec la liste), sauf ``confirm_incomplete`` : il est alors
    écrit « [non renseigné] » et consigné sur le document. Chaque appel ajoute une version."""
    await _dossier_or_404(db, dossier_id)
    drafts = DocumentDraftRepository(db)
    draft = await drafts.get(dossier_id, draft_id)
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brouillon introuvable")
    if draft.status == DraftStatus.ARCHIVE:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ce brouillon est archivé")
    if generation_in_progress(draft):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Les valeurs sont en cours de génération : attendez la fin avant d'assembler le document",
        )

    documents = GeneratedDocumentRepository(db)
    await documents.lock_draft(draft)
    template_version = await drafts.template_version(draft)
    definitions = template_definitions(template_version)
    number = await documents.next_version_number(draft)
    values, incomplete = build_values(
        definitions, await drafts.current_versions(draft.id), generated_at=datetime.now(UTC), document_version=number
    )
    if incomplete and not body.confirm_incomplete:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Des champs obligatoires ne sont pas validés : validez-les, ou confirmez la génération",
                "incomplete_fields": incomplete,
            },
        )

    prefix = f"generated-documents/{dossier_id}/{draft.id}/v{number}"
    try:
        keys = await asyncio.to_thread(render_document, template_version.file_key, values, prefix)
    except RenderWorkerUnavailableError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Le worker de rendu ne répond pas : le document n'a pas pu être généré",
        ) from None
    except RenderFailedError as error:
        await db.rollback()
        await _discard(f"{prefix}.odt", f"{prefix}.pdf")  # un dépôt partiel ne doit rien laisser
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Génération du document impossible : {error}"
        ) from error

    revision = await db.get(AnalysisRevision, draft.revision_id)
    try:
        document = await documents.add(
            dossier_id=dossier_id,
            draft_id=draft.id,
            version_number=number,
            template_id=draft.template_id,
            template_version_id=draft.template_version_id,
            template_name=template_version.name,
            template_version_number=template_version.version_number,
            analysis_id=draft.analysis_id,
            revision_id=draft.revision_id,
            revision_number=revision.number,
            file_name=_file_name(template_version.name, number),
            odt_key=keys["odt_key"],
            pdf_key=keys.get("pdf_key"),
            odt_size=await _size(keys["odt_key"]),
            pdf_size=await _size(keys["pdf_key"]) if keys.get("pdf_key") else None,
            values=values,
            incomplete_fields=incomplete,
            author_id=user.user_id,
        )
    except Exception:
        await db.rollback()
        await _discard(keys.get("odt_key"), keys.get("pdf_key"))
        raise
    # Journal du dossier (#169) : ni valeurs de champs ni nom de fichier, seulement des identifiants.
    events = DossierEventRepository(db)
    events.add(
        dossier_id,
        DossierEventType.DOCUMENT_GENERATED,
        user,
        {
            "document_id": str(document.id),
            "version_number": number,
            "template_name": template_version.name,
            "incomplete": bool(incomplete),
        },
    )
    await db.commit()
    return document_out(document)


@router.get("/{dossier_id}/generated-documents", response_model=list[GeneratedDocumentOut])
async def list_generated_documents(
    dossier_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    draft_id: Annotated[uuid.UUID | None, Query()] = None,
):
    """Documents générés du dossier, le plus récent d'abord ; ``draft_id`` filtre sur un brouillon."""
    await _dossier_or_404(db, dossier_id)
    return [document_out(d) for d in await GeneratedDocumentRepository(db).list_for_dossier(dossier_id, draft_id)]


async def _document_or_404(db: AsyncSession, dossier_id: uuid.UUID, document_id: uuid.UUID):
    await _dossier_or_404(db, dossier_id)
    document = await GeneratedDocumentRepository(db).get(dossier_id, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document introuvable")
    return document


@router.get("/{dossier_id}/generated-documents/{document_id}", response_model=GeneratedDocumentOut)
async def get_generated_document(
    dossier_id: uuid.UUID, document_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]
):
    return document_out(await _document_or_404(db, dossier_id, document_id))


@router.get("/{dossier_id}/generated-documents/{document_id}/file")
async def download_generated_document(
    dossier_id: uuid.UUID,
    document_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
    format: Annotated[Literal["odt", "pdf"], Query()] = "odt",
    inline: Annotated[
        bool, Query(description="Afficher dans le navigateur (aperçu PDF) au lieu de télécharger")
    ] = False,
):
    """Télécharge l'ODT (à retoucher hors de l'application) ou le PDF (export, aperçu). Interne : aucun accès
    usager n'existe."""
    document = await _document_or_404(db, dossier_id, document_id)
    key = document.odt_key if format == "odt" else document.pdf_key
    if key is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ce format n'est pas disponible")
    data, _ = await asyncio.to_thread(s3_connector.download, key)
    if not inline:
        # Un aperçu dans le navigateur n'est pas un téléchargement : seul l'export est tracé (#169).
        DossierEventRepository(db).add(
            dossier_id,
            DossierEventType.DOCUMENT_DOWNLOADED,
            user,
            {"document_id": str(document.id), "format": format},
        )
        await db.commit()
    name = f"{document.file_name}.{format}"
    disposition = "inline" if inline and format == "pdf" else "attachment"
    ascii_name = name.encode("ascii", "ignore").decode() or "document"
    return Response(
        content=data,
        media_type=ODT_TYPE if format == "odt" else PDF_TYPE,
        headers={
            "Content-Disposition": f"{disposition}; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(name)}",
            "Cache-Control": "private, no-store",
        },
    )
