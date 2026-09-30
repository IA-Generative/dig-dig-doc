"""ephemeral results table

Revision ID: 9c4e7a1d3b52
Revises: f8a9b0c1d2e3
Create Date: 2026-09-30 15:38:02.009759

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "9c4e7a1d3b52"
down_revision: str | None = "f8a9b0c1d2e3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ephemeral_results",
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("run_id"),
    )
    op.create_index(op.f("ix_ephemeral_results_expires_at"), "ephemeral_results", ["expires_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_ephemeral_results_expires_at"), table_name="ephemeral_results")
    op.drop_table("ephemeral_results")
