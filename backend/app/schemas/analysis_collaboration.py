"""Schémas du travail à plusieurs sur l'analyse de dossier (issue #118)."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class LockOut(BaseModel):
    element_id: uuid.UUID
    locked_by: str
    locked_by_name: str | None
    locked_until: datetime
    # Le verrou est à l'utilisateur courant.
    held_by_me: bool


class PresenceIn(BaseModel):
    """Battement de cœur : sur quel élément je suis, et si je le consulte ou l'édite."""

    element_id: uuid.UUID | None = None
    mode: Literal["viewing", "editing"] = "viewing"


class PresenceOut(BaseModel):
    user_id: str
    display_name: str
    element_id: uuid.UUID | None
    mode: str
    updated_at: datetime


class LiveSnapshot(BaseModel):
    """Ce que voit l'instructeur : qui est où, et quels éléments sont verrouillés."""

    presence: list[PresenceOut]
    locks: list[LockOut]
