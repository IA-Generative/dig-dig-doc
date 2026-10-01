"""Notes internes d'un dossier (issue #117, parent #106).

L'instructeur consigne des observations sur un dossier (« pièce vérifiée par
téléphone », « montant à revoir »). Elles sont **internes** : jamais exposées
côté usager (#96). Une note est **versionnée** en ajout seul : modifier ou
restaurer ajoute une version, rien n'est écrasé ; « supprimer » archive.

Une note peut, **sur demande**, être analysée par le worker pour proposer des
mises à jour de l'analyse de dossier (propositions confirmées par l'utilisateur,
#114). Le suivi de cette analyse est porté par la note (``analysis_status``).
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

# Suivi de l'analyse d'une note par le worker (chaîne, pas un type ENUM : pas
# de migration de type à chaque évolution).
NOTE_ANALYSIS_RUNNING = "en_cours"
NOTE_ANALYSIS_DONE = "terminé"
NOTE_ANALYSIS_FAILED = "échec"


class DossierNote(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "dossier_notes"

    dossier_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("dossiers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    # « Supprimer » une note l'archive : son historique est conservé.
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    # Analyse de la note par le worker pour proposer des mises à jour (sur demande).
    analysis_status: Mapped[str | None] = mapped_column(String, nullable=True)
    analysis_requested_by: Mapped[str | None] = mapped_column(String, nullable=True)
    analysis_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Version de la note qui a été analysée.
    analysis_version_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    analysis_proposal_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    analysis_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    versions: Mapped[list["DossierNoteVersion"]] = relationship(
        order_by="DossierNoteVersion.version_number", cascade="all, delete-orphan"
    )

    @property
    def current(self) -> "DossierNoteVersion":
        return self.versions[-1]


class DossierNoteVersion(UUIDMixin, TimestampMixin, Base):
    """Version d'une note. Jamais modifiée : modifier ou restaurer en ajoute une."""

    __tablename__ = "dossier_note_versions"
    __table_args__ = (UniqueConstraint("note_id", "version_number", name="uq_dossier_note_versions_number"),)

    note_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("dossier_notes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    author_id: Mapped[str] = mapped_column(String, nullable=False)
    # Version dont celle-ci est la restauration.
    restored_from_version_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("dossier_note_versions.id", ondelete="SET NULL"), nullable=True
    )
