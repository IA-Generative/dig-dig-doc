"""Propositions de modification de l'analyse de dossier (issue #114, parent #106).

Une modification n'est jamais appliquée directement : elle passe par une
**proposition en attente** que l'utilisateur accepte, modifie ou rejette.
Chaque étape est journalisée dans ``AnalysisProposalEvent`` (ajout seul) pour
alimenter les métriques de qualité (#102).
"""

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.dossier_analysis import AnalysisElementKind


class ProposalStatus(enum.StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    MODIFIED = "modified"
    REJECTED = "rejected"


class ProposalEventKind(enum.StrEnum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    MODIFIED = "modified"
    REJECTED = "rejected"


class AnalysisProposal(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "analysis_proposals"

    analysis_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("dossier_analyses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Élément modifié par la proposition. Vide quand elle propose d'en créer un
    # nouveau (``kind`` est alors renseigné).
    element_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("analysis_elements.id", ondelete="CASCADE"), nullable=True, index=True
    )
    kind: Mapped[AnalysisElementKind] = mapped_column(
        Enum(AnalysisElementKind, name="analysis_element_kind"), nullable=False
    )
    definition_name: Mapped[str | None] = mapped_column(String, nullable=True)
    # Version retenue de l'élément au moment de la proposition : sert à
    # détecter qu'il a été modifié entre-temps (contrôle de version).
    base_version_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("analysis_element_versions.id", ondelete="SET NULL"), nullable=True
    )
    proposed_value: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    # D'où vient l'information : message de chat, note...
    source_type: Mapped[str | None] = mapped_column(String, nullable=True)
    source_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    # Qui propose (utilisateur, ou l'agent du chat pour le compte d'un utilisateur).
    proposed_by: Mapped[str] = mapped_column(String, nullable=False)
    # Contexte de génération de la proposition (métriques par prompt et modèle).
    model: Mapped[str | None] = mapped_column(String, nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[ProposalStatus] = mapped_column(
        Enum(ProposalStatus, name="proposal_status"), nullable=False, default=ProposalStatus.PENDING, index=True
    )
    decided_by: Mapped[str | None] = mapped_column(String, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Version créée par l'acceptation (ou la modification), et élément créé
    # quand la proposition en ajoutait un.
    resulting_version_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("analysis_element_versions.id", ondelete="SET NULL"), nullable=True
    )
    resulting_element_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("analysis_elements.id", ondelete="SET NULL"), nullable=True
    )


class AnalysisProposalEvent(UUIDMixin, TimestampMixin, Base):
    """Journal des décisions, en ajout seul : jamais modifié ni supprimé
    (hors suppression du dossier)."""

    __tablename__ = "analysis_proposal_events"

    proposal_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("analysis_proposals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[ProposalEventKind] = mapped_column(Enum(ProposalEventKind, name="proposal_event_kind"), nullable=False)
    actor_id: Mapped[str] = mapped_column(String, nullable=False)
    # Valeur proposée (PROPOSED), valeur finale retenue (ACCEPTED, MODIFIED)
    # ou valeur proposée rejetée (REJECTED).
    value: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Durée entre la proposition et la décision (vide pour PROPOSED).
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    model: Mapped[str | None] = mapped_column(String, nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String, nullable=True)
