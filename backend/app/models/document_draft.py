"""Brouillon de document : les valeurs des champs d'un modèle pour un dossier (issue #140, parent #107).

- ``DocumentDraft`` : un modèle (version précise) rempli pour un dossier, à partir d'une **révision**
  précise de l'analyse (``AnalysisRevision`` : une version retenue par élément).
- ``DocumentFieldVersion`` : valeurs successives d'un champ, en **ajout seul** (jamais modifiée) ;
  la dernière version est l'état courant du champ.
- ``DocumentFieldEvent`` : journal des décisions par champ (proposé, accepté, modifié, rejeté…), en
  ajout seul, pour les métriques de qualité (#145). Interne : jamais exposé côté usager (#96).
"""

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Identity,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class DraftStatus(enum.StrEnum):
    BROUILLON = "brouillon"
    # Posés par l'assemblage du fichier (#143).
    GENERE = "généré"
    ARCHIVE = "archivé"


class FieldStatus(enum.StrEnum):
    NON_RENSEIGNE = "non_renseigné"
    PROPOSE = "proposé"
    VALIDE = "validé"


class FieldOrigin(enum.StrEnum):
    # Donnée de l'analyse ou métadonnée du dossier.
    ANALYSIS = "analysis"
    # Proposé par l'agent de génération (#141).
    AGENT = "agent"
    INSTRUCTOR = "instructor"


class FieldEventKind(enum.StrEnum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    MODIFIED = "modified"
    REJECTED = "rejected"
    REGENERATED = "regenerated"
    RESTORED = "restored"


class DocumentDraft(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "document_drafts"

    dossier_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("dossiers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("dossier_analyses.id", ondelete="CASCADE"), nullable=False
    )
    # Instantané de l'analyse dont le brouillon est tiré : l'analyse peut évoluer ensuite, le brouillon reste lié.
    revision_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("analysis_revisions.id", ondelete="CASCADE"), nullable=False
    )
    # Pas de suppression en cascade : un modèle est archivé, jamais supprimé.
    template_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("document_templates.id", ondelete="RESTRICT"), nullable=False
    )
    template_version_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("document_template_versions.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[DraftStatus] = mapped_column(String, nullable=False, default=DraftStatus.BROUILLON)
    created_by: Mapped[str] = mapped_column(String, nullable=False)

    # Génération des valeurs par l'agent (#141), suivie ici comme l'analyse d'une note : une seule à la fois.
    generation_status: Mapped[str | None] = mapped_column(String, nullable=True)
    generation_requested_by: Mapped[str | None] = mapped_column(String, nullable=True)
    generation_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    generation_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    generation_proposal_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Champs pour lesquels l'agent n'a rien trouvé (jamais inventé), et contexte tronqué faute de place.
    generation_missing: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    generation_truncated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    generation_prompt_version: Mapped[str | None] = mapped_column(String, nullable=True)


GENERATION_RUNNING = "en_cours"
GENERATION_DONE = "terminé"
GENERATION_FAILED = "échec"


class DocumentFieldVersion(UUIDMixin, TimestampMixin, Base):
    """Version d'un champ. Jamais modifiée : modifier, valider, rejeter ou restaurer en ajoute une."""

    __tablename__ = "document_field_versions"
    __table_args__ = (
        UniqueConstraint("draft_id", "field_name", "version_number", name="uq_document_field_versions_number"),
    )

    draft_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("document_drafts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    field_name: Mapped[str] = mapped_column(String, nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    # Texte, nombre, booléen ou liste selon le type du champ ; vide tant que le champ n'est pas renseigné.
    value: Mapped[Any | None] = mapped_column(JSONB(none_as_null=True), nullable=True)
    status: Mapped[FieldStatus] = mapped_column(String, nullable=False)
    origin: Mapped[FieldOrigin] = mapped_column(String, nullable=False)
    # D'où vient la valeur : éléments de l'analyse, notes, pages ou métadonnée.
    sources: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    author_id: Mapped[str | None] = mapped_column(String, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    restored_from_version_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("document_field_versions.id", ondelete="SET NULL"), nullable=True
    )
    # Origine « agent » : version du prompt et modèle (métriques, #145).
    prompt_version: Mapped[str | None] = mapped_column(String, nullable=True)
    model: Mapped[str | None] = mapped_column(String, nullable=True)


class DocumentFieldEvent(UUIDMixin, TimestampMixin, Base):
    """Journal des décisions sur un champ. Jamais modifié ni supprimé."""

    __tablename__ = "document_field_events"

    # Ordre d'insertion : les événements d'une même transaction ont le même ``created_at``.
    seq: Mapped[int] = mapped_column(BigInteger, Identity(always=True), nullable=False)
    draft_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("document_drafts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    field_name: Mapped[str] = mapped_column(String, nullable=False)
    kind: Mapped[FieldEventKind] = mapped_column(String, nullable=False)
    version_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("document_field_versions.id", ondelete="SET NULL"), nullable=True
    )
    author_id: Mapped[str | None] = mapped_column(String, nullable=True)
    # Pour une décision : secondes écoulées depuis la proposition qu'elle tranche.
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String, nullable=True)
    model: Mapped[str | None] = mapped_column(String, nullable=True)
    sources: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    # Consigne de régénération, motif de rejet, ou précision (recopie dans l'analyse…).
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
