import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Response, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors import s3_connector
from app.core.security.factory import RequestContext, get_current_user
from app.db import get_db
from app.models.report import ReportType
from app.repositories.report_repository import ReportRepository
from app.schemas.report import ReportOut

router = APIRouter(prefix="/reports", tags=["Reports"], dependencies=[Depends(get_current_user)])


def _user_display(user: RequestContext) -> str:
    full_name = f"{user.first_name} {user.last_name}".strip()
    return full_name or user.email or user.user_id


@router.post("", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
async def create_report(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
    type: Annotated[ReportType, Form()],
    title: Annotated[str, Form()],
    description: Annotated[str, Form()],
    screenshot: UploadFile | None = None,
) -> ReportOut:
    screenshot_key = None
    if screenshot is not None:
        data = await screenshot.read()
        screenshot_key = f"reports/{uuid.uuid4()}-{screenshot.filename or 'screenshot'}"
        # boto3 est synchrone : hors du threadpool, cet appel bloquerait la
        # boucle asyncio le temps de l'upload.
        await run_in_threadpool(
            s3_connector.upload, screenshot_key, data, screenshot.content_type or "application/octet-stream"
        )
    return await ReportRepository(db).create(
        user_id=user.user_id,
        user_display=_user_display(user),
        type=type,
        title=title,
        description=description,
        screenshot_key=screenshot_key,
    )


@router.get("", response_model=list[ReportOut])
async def list_my_reports(
    db: Annotated[AsyncSession, Depends(get_db)], user: Annotated[RequestContext, Depends(get_current_user)]
) -> list[ReportOut]:
    return list(await ReportRepository(db).list_mine(user.user_id))


@router.get("/{report_id}/screenshot")
async def get_report_screenshot(
    report_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
):
    """Relaie la capture d'écran jointe depuis S3 - jamais d'URL S3 signée
    renvoyée au frontend, même principe que les captures de page de
    dossier."""
    repository = ReportRepository(db)
    report = await repository.get(report_id)
    if report is None or (report.user_id != user.user_id and not user.is_admin):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Signalement introuvable")
    if report.screenshot_key is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Capture introuvable")
    data, content_type = await run_in_threadpool(s3_connector.download, report.screenshot_key)
    return Response(content=data, media_type=content_type)
