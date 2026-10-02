"""Prompt de l'agent de génération des valeurs de champs (issue #141, parent #107).

Un seul prompt générique, complété à l'exécution par la consigne de chaque champ (qui vit avec la version du
modèle de document, #138). Versionné en ajout seul : modifier ou restaurer ajoute une version, rien n'est écrasé.
Tant qu'aucune version n'existe, le prompt par défaut (``app.services.generation_prompt``) s'applique.
"""

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class GenerationPromptVersion(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "generation_prompt_versions"
    __table_args__ = (UniqueConstraint("key", "version_number", name="uq_generation_prompt_versions_number"),)

    # Prépare d'autres prompts de génération sans nouvelle table ; un seul aujourd'hui.
    key: Mapped[str] = mapped_column(String, nullable=False, default="document_fields")
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    author_id: Mapped[str] = mapped_column(String, nullable=False)
    restored_from_version_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("generation_prompt_versions.id", ondelete="SET NULL"), nullable=True
    )
