"""Routes d'administration des modèles de document (issue #138, parent #107).

Réservées aux administrateurs. Un modèle est un fichier ODT à placeholders et la définition de ses
champs, **versionnés** : modifier ou restaurer ajoute une version. À chaque import, les placeholders
du fichier (lus par le worker ``document_render``) sont comparés aux champs définis, dans les deux
sens : un écart n'est jamais ignoré en silence, il refuse la version avec un rapport lisible."""

import asyncio
import io
import uuid
import zipfile
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from pydantic import TypeAdapter, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.celery_client import RenderWorkerUnavailableError, TemplateExtractionError, extract_template_fields
from app.connectors import s3_connector
from app.core.security.admin import require_admin
from app.core.security.factory import RequestContext
from app.db import get_db
from app.models.document_template import DocumentTemplate
from app.repositories.analyse_repository import AnalyseRepository
from app.repositories.document_template_repository import (
    DocumentTemplateRepository,
    TemplateArchivedError,
    TemplateNameTakenError,
    placeholder_report,
    template_out,
)
from app.schemas.document_template import (
    FieldDefinition,
    FieldList,
    TemplateInspectOut,
    TemplateOut,
    TemplateRestoreIn,
    TemplateVersionOut,
)
from app.services.document_template_sources import definitions_of, unknown_sources

ODT_MIME = "application/vnd.oasis.opendocument.text"
MAX_TEMPLATE_BYTES = 10 * 1024 * 1024


router = APIRouter(prefix="/admin/document-templates", tags=["Admin"], dependencies=[Depends(require_admin)])


def _unprocessable(detail) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)


async def _template_or_404(db: AsyncSession, template_id: uuid.UUID) -> DocumentTemplate:
    template = await DocumentTemplateRepository(db).get(template_id)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Modèle introuvable")
    return template


async def _read_odt(file: UploadFile) -> bytes:
    """Contenu du fichier déposé, vérifié sommairement : LibreOffice convertirait n'importe quel texte."""
    data = await file.read(MAX_TEMPLATE_BYTES + 1)
    if len(data) > MAX_TEMPLATE_BYTES:
        raise _unprocessable(f"Le fichier dépasse {MAX_TEMPLATE_BYTES // (1024 * 1024)} Mo")
    try:
        mimetype = zipfile.ZipFile(io.BytesIO(data)).read("mimetype")
    except (zipfile.BadZipFile, KeyError):
        raise _unprocessable("Le fichier n'est pas un document ODT") from None
    if mimetype.strip() != ODT_MIME.encode():
        raise _unprocessable("Le fichier n'est pas un document texte ODT (LibreOffice Writer)") from None
    return data


def _parse_fields(raw: str) -> list[FieldDefinition]:
    try:
        return TypeAdapter(FieldList).validate_json('{"fields":' + raw + "}").fields
    except ValidationError as error:
        raise _unprocessable([{"loc": e["loc"][1:], "msg": e["msg"]} for e in error.errors()]) from error


async def _extract_placeholders(data: bytes) -> list[str]:
    """Fait lire le fichier par le worker (il en connaît la syntaxe) : dépôt temporaire dans S3."""
    key = f"document-templates/tmp/{uuid.uuid4()}.odt"
    await asyncio.to_thread(s3_connector.upload, key, data, ODT_MIME)
    try:
        return await asyncio.to_thread(extract_template_fields, key)
    except RenderWorkerUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Le worker de rendu ne répond pas : impossible de lire le modèle pour l'instant",
        ) from None
    except TemplateExtractionError as error:
        raise _unprocessable(f"Modèle illisible : {error}") from error
    finally:
        await asyncio.to_thread(s3_connector.delete, key)


def _check_placeholders(placeholders: list[str], fields: list[FieldDefinition]) -> None:
    report = placeholder_report(placeholders, fields)
    if not report.ok:
        raise _unprocessable(
            {
                "message": "Les champs définis ne correspondent pas aux placeholders du fichier",
                "unknown_placeholders": report.unknown_placeholders,
                "unused_fields": report.unused_fields,
            }
        )


def _check_sources(analyse, definitions: list[FieldDefinition]) -> None:
    """Chaque source « analyse » doit désigner un élément que l'analyse du modèle définit."""
    unknown = unknown_sources(analyse, definitions)
    if unknown:
        raise _unprocessable(
            {
                "message": "Des champs désignent des éléments que l'analyse ne définit pas",
                "unknown_sources": unknown,
            }
        )


def _file_key(template_id: uuid.UUID, version_number: int) -> str:
    return f"document-templates/{template_id}/v{version_number}.odt"


@router.post("/inspect", response_model=TemplateInspectOut)
async def inspect_template_file(file: Annotated[UploadFile, File()]):
    """Lit un fichier sans rien enregistrer : renvoie ses placeholders, point de départ de la
    définition des champs (il faut les connaître pour les définir)."""
    data = await _read_odt(file)
    return TemplateInspectOut(
        placeholders=await _extract_placeholders(data), file_name=file.filename or "modele.odt", file_size=len(data)
    )


@router.get("", response_model=list[TemplateOut])
async def list_templates(
    db: Annotated[AsyncSession, Depends(get_db)],
    analyse_id: Annotated[uuid.UUID | None, Query(description="Seulement les modèles de cette analyse")] = None,
    include_archived: Annotated[bool, Query()] = False,
):
    templates = await DocumentTemplateRepository(db).list_all(analyse_id=analyse_id, include_archived=include_archived)
    return [template_out(t) for t in templates]


@router.get("/analyses/{analyse_id}/definitions")
async def analyse_definitions(analyse_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]):
    """Les éléments que l'analyse définit (entités, labels, agents) : les choix possibles pour la source d'un champ."""
    analyse = await AnalyseRepository(db).get(analyse_id)
    if analyse is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analyse introuvable")
    return definitions_of(analyse)


@router.post("", response_model=TemplateOut, status_code=status.HTTP_201_CREATED)
async def create_template(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(require_admin)],
    analyse_id: Annotated[uuid.UUID, Form(description="Analyse à laquelle appartient le modèle")],
    name: Annotated[str, Form(min_length=1, max_length=200)],
    fields: Annotated[str, Form(description="Liste JSON de définitions de champs")],
    file: Annotated[UploadFile, File()],
    description: Annotated[str, Form(max_length=2000)] = "",
    generation_instructions: Annotated[str, Form(max_length=5000)] = "",
):
    """Crée un modèle **dans une analyse** : il ne servira qu'aux dossiers de cette analyse."""
    analyse = await AnalyseRepository(db).get(analyse_id)
    if analyse is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analyse introuvable")
    definitions = _parse_fields(fields)
    _check_sources(analyse, definitions)
    data = await _read_odt(file)
    placeholders = await _extract_placeholders(data)
    _check_placeholders(placeholders, definitions)

    uploaded: list[str] = []

    def key_for(template_id: uuid.UUID) -> str:
        key = _file_key(template_id, 1)
        uploaded.append(key)
        return key

    try:
        template = await DocumentTemplateRepository(db).create(
            user_id=user.user_id,
            analyse_id=analyse_id,
            name=name.strip(),
            description=description.strip(),
            generation_instructions=generation_instructions.strip(),
            fields=definitions,
            placeholders=placeholders,
            file_key_for=key_for,
            file_name=file.filename or "modele.odt",
            file_size=len(data),
        )
    except TemplateNameTakenError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Un modèle porte déjà ce nom") from None
    # Le fichier n'est déposé qu'une fois la base d'accord : pas d'objet orphelin si le nom est pris.
    await asyncio.to_thread(s3_connector.upload, template.current.file_key, data, ODT_MIME)
    return template_out(template)


@router.get("/{template_id}", response_model=TemplateOut)
async def get_template(template_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]):
    return template_out(await _template_or_404(db, template_id))


@router.get("/{template_id}/versions", response_model=list[TemplateVersionOut])
async def list_template_versions(template_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]):
    return (await _template_or_404(db, template_id)).versions


@router.post("/{template_id}/versions", response_model=TemplateOut, status_code=status.HTTP_201_CREATED)
async def add_template_version(
    template_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(require_admin)],
    name: Annotated[str, Form(min_length=1, max_length=200)],
    fields: Annotated[str, Form(description="Liste JSON de définitions de champs")],
    file: Annotated[UploadFile | None, File()] = None,
    description: Annotated[str, Form(max_length=2000)] = "",
    generation_instructions: Annotated[str, Form(max_length=5000)] = "",
):
    """Ajoute une version avec l'état complet souhaité (nom, champs, consignes). Sans fichier, la
    version garde celui de la version courante ; avec un fichier, il remplace l'ancien pour cette version."""
    template = await _template_or_404(db, template_id)
    definitions = _parse_fields(fields)
    current = template.current
    if template.analyse_id is not None:
        analyse = await AnalyseRepository(db).get(template.analyse_id)
        if analyse is not None:
            _check_sources(analyse, definitions)
    data: bytes | None = None
    if file is not None and file.filename:
        data = await _read_odt(file)
        placeholders = await _extract_placeholders(data)
        file_key = _file_key(template.id, current.version_number + 1)
        file_name, file_size = file.filename, len(data)
    else:
        placeholders, file_key, file_name, file_size = (
            current.placeholders,
            current.file_key,
            current.file_name,
            current.file_size,
        )
    _check_placeholders(placeholders, definitions)
    try:
        updated = await DocumentTemplateRepository(db).add_version(
            template,
            user_id=user.user_id,
            name=name.strip(),
            description=description.strip(),
            generation_instructions=generation_instructions.strip(),
            fields=definitions,
            placeholders=placeholders,
            file_key=file_key,
            file_name=file_name,
            file_size=file_size,
        )
    except TemplateArchivedError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ce modèle est archivé") from None
    except TemplateNameTakenError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Un modèle porte déjà ce nom") from None
    if data is not None:
        await asyncio.to_thread(s3_connector.upload, file_key, data, ODT_MIME)
    return template_out(updated)


@router.post("/{template_id}/restore", response_model=TemplateOut)
async def restore_template_version(
    template_id: uuid.UUID,
    body: TemplateRestoreIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(require_admin)],
):
    """Restaure une version antérieure : ajoute une version qui en reprend tout le contenu (fichier compris)."""
    template = await _template_or_404(db, template_id)
    version = next((v for v in template.versions if v.id == body.version_id), None)
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version introuvable pour ce modèle")
    try:
        updated = await DocumentTemplateRepository(db).add_version(
            template,
            user_id=user.user_id,
            name=version.name,
            description=version.description,
            generation_instructions=version.generation_instructions,
            fields=TypeAdapter(FieldList).validate_python({"fields": version.fields}).fields,
            placeholders=version.placeholders,
            file_key=version.file_key,
            file_name=version.file_name,
            file_size=version.file_size,
            restored_from=version.id,
        )
    except TemplateArchivedError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ce modèle est archivé") from None
    except TemplateNameTakenError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un autre modèle porte maintenant le nom de cette version : renommez-le d'abord",
        ) from None
    return template_out(updated)


@router.post("/{template_id}/archive", response_model=TemplateOut)
async def archive_template(template_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]):
    template = await _template_or_404(db, template_id)
    return template_out(await DocumentTemplateRepository(db).set_archived(template, True))


@router.post("/{template_id}/unarchive", response_model=TemplateOut)
async def unarchive_template(template_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]):
    template = await _template_or_404(db, template_id)
    return template_out(await DocumentTemplateRepository(db).set_archived(template, False))


@router.get("/{template_id}/versions/{version_number}/file")
async def download_template_file(
    template_id: uuid.UUID, version_number: int, db: Annotated[AsyncSession, Depends(get_db)]
):
    template = await _template_or_404(db, template_id)
    version = next((v for v in template.versions if v.version_number == version_number), None)
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version introuvable pour ce modèle")
    data, _ = await asyncio.to_thread(s3_connector.download, version.file_key)
    safe_name = version.file_name.replace('"', "").replace("\r", "").replace("\n", "")
    return Response(
        content=data, media_type=ODT_MIME, headers={"Content-Disposition": f'attachment; filename="{safe_name}"'}
    )
