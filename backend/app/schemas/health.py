from typing import Literal

from pydantic import BaseModel


class Health(BaseModel):
    name: str
    status: Literal["healthy", "unhealthy"]
    extras: dict[str, str] = {}


class HealthReport(BaseModel):
    name: str
    status: Literal["healthy", "unhealthy"]
    dependencies: list[Health]
