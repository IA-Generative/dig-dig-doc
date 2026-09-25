"""cgu_acceptances table

Revision ID: d6e7f8a9b0c1
Revises: c5d6e7f8a9b0
Create Date: 2026-09-25 20:00:00.000000

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "d6e7f8a9b0c1"
down_revision: str | None = "c5d6e7f8a9b0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cgu_acceptances",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("cgu_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "accepted_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["cgu_id"], ["cgus.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "cgu_id", name="uq_cgu_acceptance_user_cgu"),
    )
    op.create_index("ix_cgu_acceptances_user_id", "cgu_acceptances", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_cgu_acceptances_user_id", table_name="cgu_acceptances")
    op.drop_table("cgu_acceptances")
