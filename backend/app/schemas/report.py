import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.report import ReportStatus, ReportType


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: ReportType
    title: str
    description: str
    status: ReportStatus
    has_screenshot: bool
    admin_response: str | None
    created_at: datetime


class ReportAdminOut(ReportOut):
    user_display: str
    responded_by: str | None


class ReportUpdate(BaseModel):
    status: ReportStatus
    admin_response: str | None = None
