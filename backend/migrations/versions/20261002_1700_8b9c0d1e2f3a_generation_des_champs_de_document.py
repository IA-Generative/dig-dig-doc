"""génération des champs de document : prompt versionné et suivi de génération du brouillon

Revision ID: 8b9c0d1e2f3a
Revises: 7a8b9c0d1e2f
Create Date: 2026-10-02 17:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "8b9c0d1e2f3a"
down_revision: str | None = "7a8b9c0d1e2f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "generation_prompt_versions",
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("author_id", sa.String(), nullable=False),
        sa.Column("restored_from_version_id", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["restored_from_version_id"], ["generation_prompt_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key", "version_number", name="uq_generation_prompt_versions_number"),
    )
    op.add_column("document_drafts", sa.Column("generation_status", sa.String(), nullable=True))
    op.add_column("document_drafts", sa.Column("generation_requested_by", sa.String(), nullable=True))
    op.add_column("document_drafts", sa.Column("generation_requested_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("document_drafts", sa.Column("generation_error", sa.Text(), nullable=True))
    op.add_column("document_drafts", sa.Column("generation_proposal_count", sa.Integer(), nullable=True))
    op.add_column(
        "document_drafts", sa.Column("generation_missing", postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )
    op.add_column(
        "document_drafts",
        sa.Column("generation_truncated", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column("document_drafts", sa.Column("generation_prompt_version", sa.String(), nullable=True))


def downgrade() -> None:
    for column in (
        "generation_prompt_version",
        "generation_truncated",
        "generation_missing",
        "generation_proposal_count",
        "generation_error",
        "generation_requested_at",
        "generation_requested_by",
        "generation_status",
    ):
        op.drop_column("document_drafts", column)
    op.drop_table("generation_prompt_versions")
