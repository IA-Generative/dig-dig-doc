import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, computed_field

from app.services.notification_messages import KIND_CATEGORY


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: str
    # ``null`` quand la personne n'a plus accès au dossier (issue #177) : la notification reste dans sa liste, sans
    # lien ni nom (« Dossier non accessible »).
    dossier_id: uuid.UUID | None
    dossier_name: str | None
    accessible: bool = True
    message: str
    created_at: datetime
    read_at: datetime | None

    @computed_field
    @property
    def category(self) -> str:
        return KIND_CATEGORY[self.kind]


class UnreadCountOut(BaseModel):
    total: int
    # Non lues par catégorie : assignment, deadline, status, analysis, reminder.
    by_category: dict[str, int]


class MarkedOut(BaseModel):
    marked: int
