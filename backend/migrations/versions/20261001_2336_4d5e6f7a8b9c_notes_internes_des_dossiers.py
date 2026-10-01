"""notes internes des dossiers

Revision ID: 4d5e6f7a8b9c
Revises: 3c4d5e6f7a8b
Create Date: 2026-10-01 23:36:31.513351

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "4d5e6f7a8b9c"
down_revision: str | None = "3c4d5e6f7a8b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "dossier_notes",
        sa.Column("dossier_id", sa.UUID(), nullable=False),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("archived", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("analysis_status", sa.String(), nullable=True),
        sa.Column("analysis_requested_by", sa.String(), nullable=True),
        sa.Column("analysis_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("analysis_version_number", sa.Integer(), nullable=True),
        sa.Column("analysis_proposal_count", sa.Integer(), nullable=True),
        sa.Column("analysis_error", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["dossier_id"], ["dossiers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_dossier_notes_dossier_id"), "dossier_notes", ["dossier_id"], unique=False)
    op.create_table(
        "dossier_note_versions",
        sa.Column("note_id", sa.UUID(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("author_id", sa.String(), nullable=False),
        sa.Column("restored_from_version_id", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["note_id"], ["dossier_notes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["restored_from_version_id"], ["dossier_note_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("note_id", "version_number", name="uq_dossier_note_versions_number"),
    )
    op.create_index(op.f("ix_dossier_note_versions_note_id"), "dossier_note_versions", ["note_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_dossier_note_versions_note_id"), table_name="dossier_note_versions")
    op.drop_table("dossier_note_versions")
    op.drop_index(op.f("ix_dossier_notes_dossier_id"), table_name="dossier_notes")
    op.drop_table("dossier_notes")
