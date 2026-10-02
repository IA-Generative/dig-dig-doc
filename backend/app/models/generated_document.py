"""Document généré à partir d'un brouillon (issue #143, parent #107).

Un document est le **résultat figé** d'un assemblage : le modèle (version précise) rempli par les valeurs
**validées** du brouillon, en ODT et en PDF. Régénérer ajoute une version, l'ancienne reste. Il garde ce qui
l'a produit (révision de l'analyse source, valeurs utilisées, champs obligatoires non validés le cas échéant)
et reste **interne** : ni route usager ni diffusion (#96, #97, #105).
"""

import uuid
from typing import Any

from sqlalchemy import BigInteger, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin

VISIBILITY_INTERNAL = "interne"


class GeneratedDocument(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "generated_documents"
    __table_args__ = (UniqueConstraint("draft_id", "version_number", name="uq_generated_documents_number"),)

    # Lié à un dossier, supprimé avec lui (lignes par cascade, fichiers S3 par DossierRepository.delete_dossier).
    dossier_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("dossiers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    draft_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("document_drafts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    template_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("document_templates.id", ondelete="RESTRICT"), nullable=False
    )
    template_version_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("document_template_versions.id", ondelete="RESTRICT"), nullable=False
    )
    # Recopiés pour l'affichage : le document reste lisible même si le modèle est renommé.
    template_name: Mapped[str] = mapped_column(String, nullable=False)
    template_version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    # Révision de l'analyse dont viennent les valeurs (« version N de l'analyse »).
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("dossier_analyses.id", ondelete="CASCADE"), nullable=False
    )
    revision_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("analysis_revisions.id", ondelete="CASCADE"), nullable=False
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    file_name: Mapped[str] = mapped_column(String, nullable=False)
    odt_key: Mapped[str] = mapped_column(String, nullable=False)
    pdf_key: Mapped[str | None] = mapped_column(String, nullable=True)
    odt_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    pdf_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    # Les valeurs écrites dans le document, telles que passées au worker : le contenu est figé et traçable.
    values: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    # Champs obligatoires pas encore validés au moment de la génération (confirmée explicitement).
    incomplete_fields: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    visibility: Mapped[str] = mapped_column(String, nullable=False, default=VISIBILITY_INTERNAL)
    author_id: Mapped[str] = mapped_column(String, nullable=False)
