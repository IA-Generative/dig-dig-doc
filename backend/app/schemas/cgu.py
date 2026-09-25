import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CguOut(BaseModel):
    """Version active des CGU — route publique."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    content: str
    version: int
    published_at: datetime | None


class CguAdminOut(BaseModel):
    """Version des CGU — vue admin (inclut is_active, created_by)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    content: str
    version: int
    is_active: bool
    published_at: datetime | None
    created_by: str | None
    created_at: datetime


class CguCreate(BaseModel):
    content: str


class CguUpdate(BaseModel):
    content: str


class CguAcceptanceStatus(BaseModel):
    """Statut d'acceptation des CGU pour l'utilisateur courant.

    ``accepted`` vaut ``True`` si l'utilisateur a accepté la version
    actuellement active. Si aucune version n'est active, ``accepted``
    vaut ``True`` (pas de CGU à accepter) et ``cgu`` est ``None``.
    """

    accepted: bool
    cgu: CguOut | None = None
