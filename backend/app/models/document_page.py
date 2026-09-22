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


class BoundingBoxMixin:
    """Bbox normalisée (0-1, origine en haut à gauche) sur une page ou un
    document. Colonnes à plat plutôt que JSONB : reste filtrable/indexable,
    et exposée aux schémas Pydantic comme un seul champ `bbox` via cette
    property (from_attributes la lit comme un attribut normal)."""

    x_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    y_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    x_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    y_max: Mapped[float | None] = mapped_column(Float, nullable=True)

    @property
    def bbox(self) -> dict[str, float] | None:
        if self.x_min is None:
            return None
        return {"x_min": self.x_min, "y_min": self.y_min, "x_max": self.x_max, "y_max": self.y_max}


class DocumentPage(BoundingBoxMixin, UUIDMixin, TimestampMixin, Base):
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


class DocumentPrediction(BoundingBoxMixin, UUIDMixin, TimestampMixin, Base):
    __tablename__ = "document_predictions"

    document_page_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("document_pages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[PredictionKind] = mapped_column(Enum(PredictionKind, name="prediction_kind"), nullable=False)
    # Nom du label/de l'entité prédite (ex: "CNI", "nom") - texte libre
    # plutôt que FK vers LabelDefinition/EntityDefinition : la prédiction
    # doit survivre même si la définition est ensuite modifiée/supprimée.
    name: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    page: Mapped["DocumentPage"] = relationship(back_populates="predictions")
    validations: Mapped[list["PredictionValidation"]] = relationship(
        back_populates="prediction", cascade="all, delete-orphan", order_by="PredictionValidation.created_at"
    )


class PredictionValidation(BoundingBoxMixin, UUIDMixin, TimestampMixin, Base):
    """Historique de validation humaine d'une prédiction : chaque ligne est un
    événement (validation, correction ou rejet), jamais modifiée après coup -
    la dernière ligne fait foi, comme le versioning de FieldVersion."""

    __tablename__ = "prediction_validations"

    prediction_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("document_predictions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    validator_user_id: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[PredictionValidationStatus] = mapped_column(
        Enum(PredictionValidationStatus, name="prediction_validation_status"), nullable=False
    )
    corrected_value: Mapped[str | None] = mapped_column(Text, nullable=True)

    prediction: Mapped["DocumentPrediction"] = relationship(back_populates="validations")
