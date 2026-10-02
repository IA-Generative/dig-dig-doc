"""documents générés : ODT et PDF figés à partir d'un brouillon

Revision ID: 9c0d1e2f3a4b
Revises: 8b9c0d1e2f3a
Create Date: 2026-10-02 19:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "9c0d1e2f3a4b"
down_revision: str | None = "8b9c0d1e2f3a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "generated_documents",
        sa.Column("dossier_id", sa.UUID(), nullable=False),
        sa.Column("draft_id", sa.UUID(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("template_id", sa.UUID(), nullable=False),
        sa.Column("template_version_id", sa.UUID(), nullable=False),
        sa.Column("template_name", sa.String(), nullable=False),
        sa.Column("template_version_number", sa.Integer(), nullable=False),
        sa.Column("analysis_id", sa.UUID(), nullable=False),
        sa.Column("revision_id", sa.UUID(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("file_name", sa.String(), nullable=False),
        sa.Column("odt_key", sa.String(), nullable=False),
        sa.Column("pdf_key", sa.String(), nullable=True),
        sa.Column("odt_size", sa.BigInteger(), nullable=True),
        sa.Column("pdf_size", sa.BigInteger(), nullable=True),
        sa.Column("values", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("incomplete_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("visibility", sa.String(), nullable=False),
        sa.Column("author_id", sa.String(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["dossier_id"], ["dossiers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["draft_id"], ["document_drafts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["template_id"], ["document_templates.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["template_version_id"], ["document_template_versions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["analysis_id"], ["dossier_analyses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["revision_id"], ["analysis_revisions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("draft_id", "version_number", name="uq_generated_documents_number"),
    )
    op.create_index(op.f("ix_generated_documents_dossier_id"), "generated_documents", ["dossier_id"], unique=False)
    op.create_index(op.f("ix_generated_documents_draft_id"), "generated_documents", ["draft_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_generated_documents_draft_id"), table_name="generated_documents")
    op.drop_index(op.f("ix_generated_documents_dossier_id"), table_name="generated_documents")
    op.drop_table("generated_documents")
