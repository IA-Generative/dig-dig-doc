import enum
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class DossierStatus(enum.StrEnum):
    EN_ATTENTE = "en_attente"
    EN_COURS = "en_cours"
    TERMINE = "terminé"
    ARRETE = "arrêté"
    ECHEC = "échec"


class ExecutionStepKind(enum.StrEnum):
    CLASSIFICATION = "classification"
    EXTRACTION = "extraction"
    AGENT = "agent"


class ExecutionStepStatus(enum.StrEnum):
    EN_COURS = "en_cours"
    TERMINE = "terminé"
    ECHEC = "échec"


class Dossier(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "dossiers"

    name: Mapped[str] = mapped_column(String, nullable=False)
    # Une analyse est obligatoire : un dossier ne peut pas exister sans être lié à une analyse.
    analyse_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("analyses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    # Snapshot au lancement de la version de l'analyse utilisée (voir
    # AnalyseRepository.get_version : dérivée du nombre de FieldVersion).
    analyse_version: Mapped[str] = mapped_column(String, nullable=False, default="v1")
    status: Mapped[DossierStatus] = mapped_column(
        Enum(DossierStatus, name="dossier_status"), nullable=False, default=DossierStatus.EN_ATTENTE
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    execution_steps: Mapped[list["ExecutionStep"]] = relationship(
        back_populates="dossier", cascade="all, delete-orphan", order_by="ExecutionStep.started_at"
    )
    documents: Mapped[list["DossierDocument"]] = relationship(
        back_populates="dossier", cascade="all, delete-orphan", order_by="DossierDocument.created_at"
    )


class ExecutionStep(UUIDMixin, Base):
    __tablename__ = "execution_steps"

    dossier_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("dossiers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[ExecutionStepKind] = mapped_column(Enum(ExecutionStepKind, name="execution_step_kind"), nullable=False)
    label: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[ExecutionStepStatus] = mapped_column(
        Enum(ExecutionStepStatus, name="execution_step_status"), nullable=False, default=ExecutionStepStatus.EN_COURS
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Résultat produit par l'étape, présenté dans la page de résultat. Absent
    # tant que l'étape n'est pas terminée, ou pour un agent dont la sortie
    # n'est pas activée (Agent.output == False).
    output: Mapped[str | None] = mapped_column(Text, nullable=True)

    dossier: Mapped["Dossier"] = relationship(back_populates="execution_steps")


class DossierDocument(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "dossier_documents"

    dossier_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("dossiers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    size: Mapped[int] = mapped_column(BigInteger, nullable=False)

    dossier: Mapped["Dossier"] = relationship(back_populates="documents")
