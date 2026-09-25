"""Résumés automatiques de documents et de dossiers (issue #52).

Deux tables append-only (versioning) :
- ``DocumentSummary`` : une ligne par résumé généré pour un document, la
  dernière (par ``created_at``) est le résumé courant.
- ``DossierSummary`` : une ligne par résumé global d'un dossier, même
  principe.

Le statut de génération (en_attente / en_cours / terminé / échec) est
porté par ``DossierDocument.summary_status`` et ``Dossier.summary_status``
— les lignes de résumé ne sont insérées qu'en cas de succès, ce qui
évite d'avoir des résumés partiels ou d'erreur dans l'historique.
"""

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.dossier import Dossier, DossierDocument


class SummaryStatus(enum.StrEnum):
    """État de génération d'un résumé (document ou dossier)."""

    EN_ATTENTE = "en_attente"
    EN_COURS = "en_cours"
    TERMINE = "terminé"
    ECHEC = "échec"


class DocumentSummary(UUIDMixin, TimestampMixin, Base):
    """Résumé d'un document (toutes ses pages), généré par le LLM après
    extraction du texte. Append-only : chaque (re)génération insère une
    nouvelle ligne, la dernière fait foi."""

    __tablename__ = "document_summaries"

    dossier_document_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("dossier_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Modèle LLM utilisé pour générer ce résumé (traçabilité).
    model: Mapped[str | None] = mapped_column(String, nullable=True)

    document: Mapped["DossierDocument"] = relationship(back_populates="summaries")


class DossierSummary(UUIDMixin, TimestampMixin, Base):
    """Résumé global d'un dossier (tous documents confondus), généré après
    le pipeline complet. Append-only : chaque (re)génération insère une
    nouvelle ligne, la dernière fait foi."""

    __tablename__ = "dossier_summaries"

    dossier_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("dossiers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str | None] = mapped_column(String, nullable=True)

    dossier: Mapped["Dossier"] = relationship(back_populates="summaries")
