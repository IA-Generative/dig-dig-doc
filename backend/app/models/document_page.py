import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.dossier import DossierDocument


class PredictionKind(enum.StrEnum):
    LABEL = "label"
    ENTITY = "entity"


class PredictionValidationStatus(enum.StrEnum):
    VALIDATED = "validé"
    CORRECTED = "corrigé"
    REJECTED = "rejeté"


class DocumentPage(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "document_pages"

    dossier_document_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("dossier_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Contenu textuel de la page (OCR / extraction de texte).
    content: Mapped[str | None] = mapped_column(Text, nullable=True)

    document: Mapped["DossierDocument"] = relationship(back_populates="pages")
    predictions: Mapped[list["DocumentPrediction"]] = relationship(
        back_populates="page", cascade="all, delete-orphan", order_by="DocumentPrediction.created_at"
    )
    # Une page peut porter plusieurs zones (une par prédiction, potentiellement
    # d'autres plus tard) : la bbox est donc sa propre table rattachée à la
    # page plutôt que des colonnes plates dupliquées sur chaque table qui en
    # a besoin (prédiction, validation...).
    bounding_boxes: Mapped[list["BoundingBox"]] = relationship(
        back_populates="page", cascade="all, delete-orphan", order_by="BoundingBox.created_at"
    )


class BoundingBox(UUIDMixin, TimestampMixin, Base):
    """Zone normalisée (0-1, origine en haut à gauche) sur une page. Toujours
    rattachée à une DocumentPage ; une prédiction ou une validation qui en a
    une la référence par FK plutôt que d'en porter les coordonnées elle-même."""

    __tablename__ = "bounding_boxes"

    document_page_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("document_pages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    x_min: Mapped[float] = mapped_column(Float, nullable=False)
    y_min: Mapped[float] = mapped_column(Float, nullable=False)
    x_max: Mapped[float] = mapped_column(Float, nullable=False)
    y_max: Mapped[float] = mapped_column(Float, nullable=False)

    page: Mapped["DocumentPage"] = relationship(back_populates="bounding_boxes")


class DocumentPrediction(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "document_predictions"

    document_page_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("document_pages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    bounding_box_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("bounding_boxes.id", ondelete="SET NULL"), nullable=True
    )
    kind: Mapped[PredictionKind] = mapped_column(Enum(PredictionKind, name="prediction_kind"), nullable=False)
    # Nom du label/de l'entité prédite (ex: "CNI", "nom") - texte libre
    # plutôt que FK vers LabelDefinition/EntityDefinition : la prédiction
    # doit survivre même si la définition est ensuite modifiée/supprimée.
    name: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    page: Mapped["DocumentPage"] = relationship(back_populates="predictions")
    bounding_box: Mapped["BoundingBox | None"] = relationship(foreign_keys=[bounding_box_id])
    validations: Mapped[list["PredictionValidation"]] = relationship(
        back_populates="prediction", cascade="all, delete-orphan", order_by="PredictionValidation.created_at"
    )


class PredictionValidation(UUIDMixin, TimestampMixin, Base):
    """Historique de validation humaine d'une prédiction : chaque ligne est un
    événement (validation, correction ou rejet), jamais modifiée après coup -
    la dernière ligne fait foi, comme le versioning de FieldVersion. Une
    correction de zone crée sa propre BoundingBox (jamais de mutation de
    celle de la prédiction d'origine) pour garder l'historique intact."""

    __tablename__ = "prediction_validations"

    prediction_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("document_predictions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    bounding_box_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("bounding_boxes.id", ondelete="SET NULL"), nullable=True
    )
    validator_user_id: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[PredictionValidationStatus] = mapped_column(
        Enum(PredictionValidationStatus, name="prediction_validation_status"), nullable=False
    )
    corrected_value: Mapped[str | None] = mapped_column(Text, nullable=True)

    prediction: Mapped["DocumentPrediction"] = relationship(back_populates="validations")
    bounding_box: Mapped["BoundingBox | None"] = relationship(foreign_keys=[bounding_box_id])
