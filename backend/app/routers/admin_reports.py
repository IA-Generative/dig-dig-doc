import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.factory import RequestContext, get_current_user
from app.db import get_db
from app.models.report import ReportStatus, ReportType
from app.repositories.report_repository import ReportRepository
from app.schemas.pagination import Page
from app.schemas.report import ReportAdminOut, ReportUpdate

router = APIRouter(prefix="/admin/reports", tags=["Admin"], dependencies=[Depends(get_current_user)])


def _require_admin(user: RequestContext) -> None:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès réservé aux administrateurs")


@router.get("", response_model=Page[ReportAdminOut])
async def list_reports(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status_filter: ReportStatus | None = None,
    type_filter: ReportType | None = None,
) -> Page[ReportAdminOut]:
    _require_admin(user)
    reports, total = await ReportRepository(db).list_paginated(
        page=page, page_size=page_size, status_filter=status_filter, type_filter=type_filter
    )
    return Page.of(list(reports), total=total, page=page, page_size=page_size)


@router.patch("/{report_id}", response_model=ReportAdminOut)
async def update_report(
    report_id: uuid.UUID,
    body: ReportUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
) -> ReportAdminOut:
    _require_admin(user)
    repository = ReportRepository(db)
    report = await repository.get(report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Signalement introuvable")
    responded_by = user.user_id if body.admin_response else None
    return await repository.update_status(
        report, status=body.status, admin_response=body.admin_response, responded_by=responded_by
    )
