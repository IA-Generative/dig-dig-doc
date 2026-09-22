import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.dossier import ExecutionStep


class ExecutionLogLevel(enum.StrEnum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ExecutionLog(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "execution_logs"

    execution_step_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("execution_steps.id", ondelete="CASCADE"), nullable=False, index=True
    )
    level: Mapped[ExecutionLogLevel] = mapped_column(
        Enum(ExecutionLogLevel, name="execution_log_level"), nullable=False, default=ExecutionLogLevel.INFO
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)

    execution_step: Mapped["ExecutionStep"] = relationship(back_populates="logs")
