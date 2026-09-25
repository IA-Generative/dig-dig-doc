import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class Cgu(UUIDMixin, TimestampMixin, Base):
    """Conditions Générales d'Utilisation versionnées.

    Chaque version est une ligne distincte. Une seule version est active à
    la fois (``is_active=True``) ; l'historique est conservé pour
    traçabilité. Le contenu reste en Markdown pour faciliter l'édition par
    l'administrateur.
    """

    __tablename__ = "cgus"

    content: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String, nullable=True)
