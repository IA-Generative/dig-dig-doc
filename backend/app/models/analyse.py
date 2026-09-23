import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.analyse_share import AnalyseShare


class EntityType(enum.StrEnum):
    TEXTE = "texte"
    DATE = "date"
    NOMBRE = "nombre"
    BOOLEEN = "booléen"
    IDENTIFIANT = "identifiant"


class AgentTool(enum.StrEnum):
    LECTURE_DOCUMENT = "lecture_document"
    RECHERCHE_WEB = "recherche_web"
    BASE_CONNAISSANCES = "base_connaissances"
    APPEL_AGENT = "appel_agent"
    CALCULATRICE = "calculatrice"
    VERIFICATION_COHERENCE = "verification_coherence"


class VersionedField(enum.StrEnum):
    """What a FieldVersion snapshot is a previous value of. classification_*
    and extraction_* rows key off analyse_id alone (agent_id NULL); agent_*
    rows also carry the owning agent_id."""

    CLASSIFICATION_PROMPT = "classification_prompt"
    CLASSIFICATION_LABELS = "classification_labels"
    EXTRACTION_PROMPT = "extraction_prompt"
    EXTRACTION_ENTITIES = "extraction_entities"
    AGENT_PROMPT = "agent_prompt"
    AGENT_TOOLS = "agent_tools"
    AGENT_OUTPUT = "agent_output"
    AGENT_MODEL = "agent_model"


class Analyse(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "analyses"

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # Classification et extraction sont des analyses simples (un prompt
    # appliqué systématiquement, pas un agent) : un seul jeu de labels/
    # entités par analyse, embarqué directement plutôt qu'en table à part -
    # il n'y a jamais qu'une seule classification/extraction par analyse.
    classification_prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    extraction_prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")

    labels: Mapped[list["LabelDefinition"]] = relationship(
        back_populates="analyse", cascade="all, delete-orphan", order_by="LabelDefinition.created_at"
    )
    entities: Mapped[list["EntityDefinition"]] = relationship(
        back_populates="analyse", cascade="all, delete-orphan", order_by="EntityDefinition.created_at"
    )
    agents: Mapped[list["Agent"]] = relationship(
        back_populates="analyse", cascade="all, delete-orphan", order_by="Agent.created_at"
    )
    field_versions: Mapped[list["FieldVersion"]] = relationship(
        back_populates="analyse", cascade="all, delete-orphan", order_by="FieldVersion.created_at.desc()"
    )
    shares: Mapped[list["AnalyseShare"]] = relationship(
        back_populates="analyse", cascade="all, delete-orphan", order_by="AnalyseShare.created_at.desc()"
    )


class LabelDefinition(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "label_definitions"

    analyse_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    definition: Mapped[str] = mapped_column(Text, nullable=False, default="")

    analyse: Mapped["Analyse"] = relationship(back_populates="labels")


class EntityDefinition(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "entity_definitions"

    analyse_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    definition: Mapped[str] = mapped_column(Text, nullable=False, default="")
    type: Mapped[EntityType] = mapped_column(Enum(EntityType, name="entity_type"), nullable=False)

    analyse: Mapped["Analyse"] = relationship(back_populates="entities")


class Agent(UUIDMixin, TimestampMixin, Base):
    """Un agent est créé librement par l'utilisateur pour un but métier
    propre à l'analyse (cohérence, rédaction, timeline...) : nom, prompt et
    outils, sans capacité prédéfinie - à la différence de la classification
    et de l'extraction qui sont des analyses systématiques."""

    __tablename__ = "agents"

    analyse_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tools: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    # Si vrai, le résultat de cet agent est présenté comme une sortie visible
    # dans la page de résultat du dossier.
    output: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Identifiant de modèle tel que renvoyé par GET /models (id du hub LLM
    # configuré) ; NULL = pas de préférence, le hub par défaut sera utilisé.
    model: Mapped[str | None] = mapped_column(String, nullable=True)

    analyse: Mapped["Analyse"] = relationship(back_populates="agents")
    field_versions: Mapped[list["FieldVersion"]] = relationship(
        back_populates="agent", cascade="all, delete-orphan", order_by="FieldVersion.created_at.desc()"
    )


class FieldVersion(UUIDMixin, TimestampMixin, Base):
    """A snapshot of a field's *previous* value, taken right before it was
    overwritten - the same versioning treatment applies to every editable
    field of an Analyse/Agent (prompt, labels, entities, tools, output),
    not just the prompt."""

    __tablename__ = "field_versions"

    analyse_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # NULL for classification_*/extraction_* fields (owned directly by the analyse).
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=True, index=True
    )
    field: Mapped[VersionedField] = mapped_column(Enum(VersionedField, name="versioned_field"), nullable=False)
    # Shape depends on `field`: a string for *_prompt, a bool for
    # agent_output, a JSON array of {name, definition[, type]} for
    # *_labels/*_entities, a JSON array of strings for agent_tools.
    content: Mapped[dict | list | str | bool] = mapped_column(JSONB, nullable=False)

    analyse: Mapped["Analyse"] = relationship(back_populates="field_versions")
    agent: Mapped["Agent | None"] = relationship(back_populates="field_versions")
