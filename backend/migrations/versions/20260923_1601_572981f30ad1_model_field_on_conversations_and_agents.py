"""model field on agents (conversations.model already added by b2c3d4e5f6a7)

Revision ID: 572981f30ad1
Revises: b2c3d4e5f6a7
Create Date: 2026-09-23 16:01:31.905166

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "572981f30ad1"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # conversations.model was already added by b2c3d4e5f6a7 (a migration
    # written concurrently by another session, before the two histories
    # were linearized) - only agents.model is new here.
    op.add_column("agents", sa.Column("model", sa.String(), nullable=True))
    # New VersionedField member for the agent model field's version history -
    # op.add_column() never touches the enum type itself, so it has to be
    # added to the Postgres enum explicitly (see other migrations for the
    # same gotcha).
    op.execute("ALTER TYPE versioned_field ADD VALUE IF NOT EXISTS 'AGENT_MODEL'")


def downgrade() -> None:
    # Postgres doesn't support removing an enum value; the column drop is
    # still safe/reversible on its own.
    op.drop_column("agents", "model")
