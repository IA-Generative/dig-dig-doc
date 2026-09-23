import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.report import Report, ReportStatus, ReportType


class ReportRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        *,
        user_id: str,
        user_display: str,
        type: ReportType,
        title: str,
        description: str,
        screenshot_key: str | None,
    ) -> Report:
        report = Report(
            user_id=user_id,
            user_display=user_display,
            type=type,
            title=title,
            description=description,
            screenshot_key=screenshot_key,
        )
        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)
        return report

    async def get(self, report_id: uuid.UUID) -> Report | None:
        result = await self.db.execute(select(Report).where(Report.id == report_id))
        return result.scalar_one_or_none()

    async def list_mine(self, user_id: str) -> Sequence[Report]:
        result = await self.db.execute(
            select(Report).where(Report.user_id == user_id).order_by(Report.created_at.desc())
        )
        return result.scalars().all()

    async def list_mine_paginated(self, *, user_id: str, page: int, page_size: int) -> tuple[Sequence[Report], int]:
        base = select(Report).where(Report.user_id == user_id)
        count_query = select(func.count()).select_from(Report).where(Report.user_id == user_id)
        total = await self.db.scalar(count_query)
        result = await self.db.execute(
            base.order_by(Report.created_at.desc()).limit(page_size).offset((page - 1) * page_size)
        )
        return result.scalars().all(), total or 0

    async def list_paginated(
        self,
        *,
        page: int,
        page_size: int,
        status_filter: ReportStatus | None = None,
        type_filter: ReportType | None = None,
    ) -> tuple[Sequence[Report], int]:
        query = select(Report)
        count_query = select(func.count()).select_from(Report)
        if status_filter is not None:
            query = query.where(Report.status == status_filter)
            count_query = count_query.where(Report.status == status_filter)
        if type_filter is not None:
            query = query.where(Report.type == type_filter)
            count_query = count_query.where(Report.type == type_filter)

        total = await self.db.scalar(count_query)
        result = await self.db.execute(
            query.order_by(Report.created_at.desc()).limit(page_size).offset((page - 1) * page_size)
        )
        return result.scalars().all(), total or 0

    async def update_status(
        self,
        report: Report,
        *,
        status: ReportStatus,
        admin_response: str | None,
        responded_by: str | None,
    ) -> Report:
        report.status = status
        if admin_response is not None:
            report.admin_response = admin_response
            report.responded_by = responded_by
        await self.db.commit()
        await self.db.refresh(report)
        return report
