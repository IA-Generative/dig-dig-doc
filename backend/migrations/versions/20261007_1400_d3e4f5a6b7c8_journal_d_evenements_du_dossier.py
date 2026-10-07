"""journal d'événements du dossier (issue #169)

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-10-07 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "d3e4f5a6b7c8"
down_revision: str | None = "c2d3e4f5a6b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "dossier_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dossier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("actor_id", sa.String(), nullable=True),
        sa.Column("actor_name", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("seq", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["dossier_id"], ["dossiers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_dossier_events_dossier_id"), "dossier_events", ["dossier_id"], unique=False)
    op.create_index(op.f("ix_dossier_events_type"), "dossier_events", ["type"], unique=False)
    op.create_index(op.f("ix_dossier_events_actor_id"), "dossier_events", ["actor_id"], unique=False)
    op.create_index("ix_dossier_events_dossier_id_seq", "dossier_events", ["dossier_id", "seq"], unique=False)

    # Les dossiers existants reçoivent un événement de création daté de leur création (auteur inconnu),
    # pour que leur historique commence quelque part.
    op.execute(
        """
        INSERT INTO dossier_events (id, dossier_id, type, actor_id, actor_name, created_at, payload)
        SELECT gen_random_uuid(), id, 'created', NULL, NULL, created_at, '{"imported": true}'::jsonb
        FROM dossiers
        ORDER BY created_at
        """
    )


def downgrade() -> None:
    op.drop_index("ix_dossier_events_dossier_id_seq", table_name="dossier_events")
    op.drop_index(op.f("ix_dossier_events_actor_id"), table_name="dossier_events")
    op.drop_index(op.f("ix_dossier_events_type"), table_name="dossier_events")
    op.drop_index(op.f("ix_dossier_events_dossier_id"), table_name="dossier_events")
    op.drop_table("dossier_events")
