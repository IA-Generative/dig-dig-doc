"""brouillons de document : valeurs de champs versionnées et journal des décisions

Revision ID: 7a8b9c0d1e2f
Revises: 6f7a8b9c0d1e
Create Date: 2026-10-02 15:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "7a8b9c0d1e2f"
down_revision: str | None = "6f7a8b9c0d1e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_drafts",
        sa.Column("dossier_id", sa.UUID(), nullable=False),
        sa.Column("analysis_id", sa.UUID(), nullable=False),
        sa.Column("revision_id", sa.UUID(), nullable=False),
        sa.Column("template_id", sa.UUID(), nullable=False),
        sa.Column("template_version_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["dossier_id"], ["dossiers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["analysis_id"], ["dossier_analyses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["revision_id"], ["analysis_revisions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["template_id"], ["document_templates.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["template_version_id"], ["document_template_versions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_document_drafts_dossier_id"), "document_drafts", ["dossier_id"], unique=False)
    op.create_table(
        "document_field_versions",
        sa.Column("draft_id", sa.UUID(), nullable=False),
        sa.Column("field_name", sa.String(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("value", postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("origin", sa.String(), nullable=False),
        sa.Column("sources", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("author_id", sa.String(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("restored_from_version_id", sa.UUID(), nullable=True),
        sa.Column("prompt_version", sa.String(), nullable=True),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["draft_id"], ["document_drafts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["restored_from_version_id"], ["document_field_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("draft_id", "field_name", "version_number", name="uq_document_field_versions_number"),
    )
    op.create_index(op.f("ix_document_field_versions_draft_id"), "document_field_versions", ["draft_id"], unique=False)
    op.create_table(
        "document_field_events",
        sa.Column("seq", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("draft_id", sa.UUID(), nullable=False),
        sa.Column("field_name", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("version_id", sa.UUID(), nullable=True),
        sa.Column("author_id", sa.String(), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("prompt_version", sa.String(), nullable=True),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("sources", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["draft_id"], ["document_drafts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["version_id"], ["document_field_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_document_field_events_draft_id"), "document_field_events", ["draft_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_document_field_events_draft_id"), table_name="document_field_events")
    op.drop_table("document_field_events")
    op.drop_index(op.f("ix_document_field_versions_draft_id"), table_name="document_field_versions")
    op.drop_table("document_field_versions")
    op.drop_index(op.f("ix_document_drafts_dossier_id"), table_name="document_drafts")
    op.drop_table("document_drafts")
