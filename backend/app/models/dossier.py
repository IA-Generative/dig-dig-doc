import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.summary import SummaryStatus

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.document_page import DocumentPage
    from app.models.execution_log import ExecutionLog
    from app.models.summary import DocumentSummary, DossierSummary


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


class TextExtractionStatus(enum.StrEnum):
    """État du run d'extraction de texte (worker document_process,
    app.tasks.extract_document_text) pour un document - pas un
    ExecutionStep : ça tourne dès l'upload, indépendamment d'un lancement de
    dossier, et alimente les pages/bbox qu'une classification/extraction
    lira ensuite."""

    EN_ATTENTE = "en_attente"
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
    # État de génération du résumé global du dossier (issue #52).
    summary_status: Mapped[SummaryStatus] = mapped_column(
        Enum(SummaryStatus, name="summary_status"),
        nullable=False,
        default=SummaryStatus.EN_ATTENTE,
    )
    summary_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    execution_steps: Mapped[list["ExecutionStep"]] = relationship(
        back_populates="dossier", cascade="all, delete-orphan", order_by="ExecutionStep.started_at"
    )
    documents: Mapped[list["DossierDocument"]] = relationship(
        back_populates="dossier", cascade="all, delete-orphan", order_by="DossierDocument.created_at"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="dossier", cascade="all, delete-orphan", order_by="Conversation.created_at"
    )
    summaries: Mapped[list["DossierSummary"]] = relationship(
        back_populates="dossier", cascade="all, delete-orphan", order_by="DossierSummary.created_at.desc()"
    )

    @property
    def summary(self) -> "DossierSummary | None":
        """Dernier résumé généré (le plus récent par created_at), ou None."""
        return self.summaries[0] if self.summaries else None


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
    logs: Mapped[list["ExecutionLog"]] = relationship(
        back_populates="execution_step", cascade="all, delete-orphan", order_by="ExecutionLog.created_at"
    )


class DossierDocument(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "dossier_documents"

    dossier_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("dossiers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # Clé de l'objet dans le bucket S3 (le contenu du fichier n'est jamais
    # stocké en base) et type MIME déclaré à l'upload.
    s3_key: Mapped[str] = mapped_column(String, nullable=False)
    mimetype: Mapped[str] = mapped_column(String, nullable=False)
    # Nature du document (ex: "CNI", "avis d'imposition") : posée par la
    # classification documentaire de l'analyse, ou corrigée manuellement.
    label: Mapped[str | None] = mapped_column(String, nullable=True)
    text_extraction_status: Mapped[TextExtractionStatus] = mapped_column(
        Enum(TextExtractionStatus, name="text_extraction_status"),
        nullable=False,
        default=TextExtractionStatus.EN_ATTENTE,
    )
    text_extraction_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Empreinte SHA-256 du contenu du fichier, calculée par le worker
    # document_process au moment de l'extraction (les bytes sont déjà en
    # mémoire). Permet de détecter les doublons et les fichiers identiques
    # re-uploadés.
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    # État de génération du résumé du document (issue #52).
    summary_status: Mapped[SummaryStatus] = mapped_column(
        Enum(SummaryStatus, name="summary_status"),
        nullable=False,
        default=SummaryStatus.EN_ATTENTE,
    )
    summary_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    dossier: Mapped["Dossier"] = relationship(back_populates="documents")
    pages: Mapped[list["DocumentPage"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", order_by="DocumentPage.page_number"
    )
    summaries: Mapped[list["DocumentSummary"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", order_by="DocumentSummary.created_at.desc()"
    )

    @property
    def summary(self) -> "DocumentSummary | None":
        """Dernier résumé généré (le plus récent par created_at), ou None."""
        return self.summaries[0] if self.summaries else None
