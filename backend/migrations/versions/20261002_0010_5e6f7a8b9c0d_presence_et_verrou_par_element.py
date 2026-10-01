"""presence et verrou par élément

Revision ID: 5e6f7a8b9c0d
Revises: 4d5e6f7a8b9c
Create Date: 2026-10-02 00:10:58.504919

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5e6f7a8b9c0d"
down_revision: str | None = "4d5e6f7a8b9c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "analysis_presence",
        sa.Column("analysis_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("element_id", sa.UUID(), nullable=True),
        sa.Column("mode", sa.String(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["dossier_analyses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["element_id"], ["analysis_elements.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("analysis_id", "user_id"),
    )
    op.add_column("analysis_elements", sa.Column("locked_by_name", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_table("analysis_presence")
    op.drop_column("analysis_elements", "locked_by_name")
