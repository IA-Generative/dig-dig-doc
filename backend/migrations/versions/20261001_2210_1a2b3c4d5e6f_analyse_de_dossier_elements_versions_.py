"""analyse de dossier elements versions revisions

Revision ID: 1a2b3c4d5e6f
Revises: 9c4e7a1d3b52
Create Date: 2026-10-01 22:10:59.336863

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "1a2b3c4d5e6f"
down_revision: str | None = "9c4e7a1d3b52"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "dossier_analyses",
        sa.Column("dossier_id", sa.UUID(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("status", sa.Enum("BROUILLON", "VALIDEE", "FIGEE", name="dossier_analysis_status"), nullable=False),
        sa.Column("analyse_version", sa.String(), nullable=True),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("previous_analysis_id", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["dossier_id"], ["dossiers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["previous_analysis_id"], ["dossier_analyses.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dossier_id", "sequence", name="uq_dossier_analyses_dossier_id_sequence"),
    )
    op.create_index(op.f("ix_dossier_analyses_dossier_id"), "dossier_analyses", ["dossier_id"], unique=False)
    op.create_table(
        "analysis_revisions",
        sa.Column("analysis_id", sa.UUID(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(), nullable=True),
        sa.Column("author_id", sa.String(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["dossier_analyses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("analysis_id", "number", name="uq_analysis_revisions_analysis_id_number"),
    )
    op.create_index(op.f("ix_analysis_revisions_analysis_id"), "analysis_revisions", ["analysis_id"], unique=False)
    op.create_table(
        "analysis_units",
        sa.Column("analysis_id", sa.UUID(), nullable=False),
        sa.Column("kind", sa.Enum("CLASSIFICATION", "EXTRACTION", "AGENT", name="analysis_unit_kind"), nullable=False),
        sa.Column("description", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.Enum("EN_COURS", "TERMINE", "ECHEC", name="analysis_unit_status"), nullable=False),
        sa.Column("input_fingerprint", sa.String(length=64), nullable=True),
        sa.Column("element_count", sa.Integer(), nullable=False),
        sa.Column("source_unit_id", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["dossier_analyses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_unit_id"], ["analysis_units.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_analysis_units_analysis_id"), "analysis_units", ["analysis_id"], unique=False)
    op.create_index(op.f("ix_analysis_units_input_fingerprint"), "analysis_units", ["input_fingerprint"], unique=False)
    op.create_table(
        "analysis_elements",
        sa.Column("analysis_id", sa.UUID(), nullable=False),
        sa.Column("unit_id", sa.UUID(), nullable=True),
        sa.Column(
            "kind",
            sa.Enum("CLASSIFICATION", "ENTITY", "RELATION", "SYNTHESIS", "FIELD", name="analysis_element_kind"),
            nullable=False,
        ),
        sa.Column("definition_id", sa.UUID(), nullable=True),
        sa.Column("definition_name", sa.String(), nullable=True),
        sa.Column("document_id", sa.UUID(), nullable=True),
        sa.Column("first_page_number", sa.Integer(), nullable=True),
        sa.Column("source_prediction_id", sa.UUID(), nullable=True),
        sa.Column("origin_element_id", sa.UUID(), nullable=True),
        sa.Column("retained_version_id", sa.UUID(), nullable=True),
        sa.Column("latest_model_version_id", sa.UUID(), nullable=True),
        sa.Column("needs_review", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("review_reason", sa.Text(), nullable=True),
        sa.Column("locked_by", sa.String(), nullable=True),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["dossier_analyses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["dossier_documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["origin_element_id"], ["analysis_elements.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_prediction_id"], ["document_predictions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["unit_id"], ["analysis_units.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_prediction_id"),
    )
    op.create_index(op.f("ix_analysis_elements_analysis_id"), "analysis_elements", ["analysis_id"], unique=False)
    op.create_index(op.f("ix_analysis_elements_document_id"), "analysis_elements", ["document_id"], unique=False)
    op.create_index(op.f("ix_analysis_elements_unit_id"), "analysis_elements", ["unit_id"], unique=False)
    op.create_table(
        "analysis_element_versions",
        sa.Column("element_id", sa.UUID(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column(
            "origin", sa.Enum("MODEL", "INSTRUCTOR", "CARRIED_OVER", name="element_version_origin"), nullable=False
        ),
        sa.Column("prediction_id", sa.UUID(), nullable=True),
        sa.Column("author_id", sa.String(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("source_type", sa.String(), nullable=True),
        sa.Column("source_id", sa.UUID(), nullable=True),
        sa.Column("restored_from_version_id", sa.UUID(), nullable=True),
        sa.Column("origin_version_id", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["element_id"], ["analysis_elements.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["origin_version_id"], ["analysis_element_versions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["prediction_id"], ["document_predictions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["restored_from_version_id"], ["analysis_element_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("element_id", "version_number", name="uq_analysis_element_versions_number"),
    )
    op.create_index(
        op.f("ix_analysis_element_versions_element_id"), "analysis_element_versions", ["element_id"], unique=False
    )
    # Dépendance circulaire éléments <-> versions : FK posées après coup.
    op.create_foreign_key(
        "fk_analysis_elements_retained",
        "analysis_elements",
        "analysis_element_versions",
        ["retained_version_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_analysis_elements_latest_model",
        "analysis_elements",
        "analysis_element_versions",
        ["latest_model_version_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_table(
        "analysis_revision_items",
        sa.Column("revision_id", sa.UUID(), nullable=False),
        sa.Column("element_id", sa.UUID(), nullable=False),
        sa.Column("version_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["element_id"], ["analysis_elements.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["revision_id"], ["analysis_revisions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["version_id"], ["analysis_element_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("revision_id", "element_id"),
    )


def downgrade() -> None:
    op.drop_table("analysis_revision_items")
    op.drop_constraint("fk_analysis_elements_latest_model", "analysis_elements", type_="foreignkey")
    op.drop_constraint("fk_analysis_elements_retained", "analysis_elements", type_="foreignkey")
    op.drop_index(op.f("ix_analysis_element_versions_element_id"), table_name="analysis_element_versions")
    op.drop_table("analysis_element_versions")
    op.drop_index(op.f("ix_analysis_elements_unit_id"), table_name="analysis_elements")
    op.drop_index(op.f("ix_analysis_elements_document_id"), table_name="analysis_elements")
    op.drop_index(op.f("ix_analysis_elements_analysis_id"), table_name="analysis_elements")
    op.drop_table("analysis_elements")
    op.drop_index(op.f("ix_analysis_units_input_fingerprint"), table_name="analysis_units")
    op.drop_index(op.f("ix_analysis_units_analysis_id"), table_name="analysis_units")
    op.drop_table("analysis_units")
    op.drop_index(op.f("ix_analysis_revisions_analysis_id"), table_name="analysis_revisions")
    op.drop_table("analysis_revisions")
    op.drop_index(op.f("ix_dossier_analyses_dossier_id"), table_name="dossier_analyses")
    op.drop_table("dossier_analyses")
    # Les types ENUM PostgreSQL ne sont pas supprimés avec leur table.
    for name in (
        "element_version_origin",
        "analysis_element_kind",
        "analysis_unit_status",
        "analysis_unit_kind",
        "dossier_analysis_status",
    ):
        op.execute(f"DROP TYPE IF EXISTS {name}")
