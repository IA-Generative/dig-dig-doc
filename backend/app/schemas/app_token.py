import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AppTokenCreate(BaseModel):
    name: str


class AppTokenOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    created_by: str
    created_at: datetime
    revoked_at: datetime | None
    last_used_at: datetime | None


class AppTokenCreated(AppTokenOut):
    # Uniquement à la création : le jeton en clair n'est jamais stocké, donc
    # jamais renvoyé ensuite (voir AppToken.token_hash).
    token: str
