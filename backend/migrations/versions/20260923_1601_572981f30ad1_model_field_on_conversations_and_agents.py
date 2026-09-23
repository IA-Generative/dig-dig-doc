"""model field on conversations and agents

Revision ID: 572981f30ad1
Revises: a1b2c3d4e5f6
Create Date: 2026-09-23 16:01:31.905166

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "572981f30ad1"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("agents", sa.Column("model", sa.String(), nullable=True))
    op.add_column("conversations", sa.Column("model", sa.String(), nullable=True))
    # New VersionedField member for the agent model field's version history -
    # op.add_column() never touches the enum type itself, so it has to be
    # added to the Postgres enum explicitly (see other migrations for the
    # same gotcha).
    op.execute("ALTER TYPE versioned_field ADD VALUE IF NOT EXISTS 'AGENT_MODEL'")


def downgrade() -> None:
    # Postgres doesn't support removing an enum value; the column drops are
    # still safe/reversible on their own.
    op.drop_column("conversations", "model")
    op.drop_column("agents", "model")
