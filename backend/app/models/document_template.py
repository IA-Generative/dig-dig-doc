"""Modèles de document et définition de leurs champs (issue #138, parent #107).

Un modèle est un fichier ODT à placeholders (``{{ nom }}``) que le worker
``document_render`` remplit (#146). Tout ce qu'un administrateur peut modifier
(nom, description, champs, consignes, fichier) vit dans la **version** : une
version n'est jamais modifiée, modifier ou restaurer en ajoute une. Seul
l'archivage est un état du modèle.
"""

import uuid

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class DocumentTemplate(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "document_templates"

    # Un modèle appartient à **une** analyse (issue #139) : ses champs puisent dans les définitions de cette
    # analyse et seuls ses dossiers peuvent s'en servir. Vide seulement pour un modèle créé avant ce rattachement :
    # il n'est proposé à aucun dossier. Supprimer une analyse (sans dossier) supprime ses modèles.
    analyse_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=True, index=True
    )
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    # « Supprimer » un modèle l'archive : les documents déjà générés (#143) y font référence.
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    versions: Mapped[list["DocumentTemplateVersion"]] = relationship(
        order_by="DocumentTemplateVersion.version_number", cascade="all, delete-orphan"
    )

    @property
    def current(self) -> "DocumentTemplateVersion":
        return self.versions[-1]


class DocumentTemplateVersion(UUIDMixin, TimestampMixin, Base):
    """Version d'un modèle. Jamais modifiée : modifier ou restaurer en ajoute une."""

    __tablename__ = "document_template_versions"
    __table_args__ = (UniqueConstraint("template_id", "version_number", name="uq_document_template_versions_number"),)

    template_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("document_templates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    # Consignes de génération communes à tous les champs (ton, registre, langue).
    generation_instructions: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    # Définition des champs (liste de FieldDefinition sérialisées) : portée par la version,
    # donc modifiable et restaurable comme le fichier.
    fields: Mapped[list[dict]] = mapped_column(JSONB, nullable=False)
    # Placeholders trouvés dans le fichier par le worker, au moment de l'import.
    placeholders: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    # Avertissements du contrôle à l'import (issue #148) : polices absentes de l'image, champs natifs LibreOffice,
    # images. Jamais bloquants ; conservés pour les revoir à la réouverture du modèle.
    warnings: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")
    # Le fichier est partagé entre les versions qui ne le changent pas (définition seule, restauration).
    file_key: Mapped[str] = mapped_column(String, nullable=False)
    file_name: Mapped[str] = mapped_column(String, nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    author_id: Mapped[str] = mapped_column(String, nullable=False)
    restored_from_version_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("document_template_versions.id", ondelete="SET NULL"), nullable=True
    )
