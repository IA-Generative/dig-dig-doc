"""notifications des personnes (issue #174)

Revision ID: c8d9e0f1a2b3
Revises: b7c8d9e0f1a2
Create Date: 2026-10-12 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c8d9e0f1a2b3"
down_revision: str | None = "b7c8d9e0f1a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("dossier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dossier_name", sa.String(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("dedup_key", sa.String(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["dossier_id"], ["dossiers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "dedup_key", name="uq_notifications_user_dedup"),
    )
    op.create_index(op.f("ix_notifications_user_id"), "notifications", ["user_id"], unique=False)
    op.create_index(op.f("ix_notifications_dossier_id"), "notifications", ["dossier_id"], unique=False)
    op.create_index("ix_notifications_user_created", "notifications", ["user_id", "created_at"], unique=False)
    op.create_table(
        "notification_cursors",
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("last_seq", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("notification_cursors")
    op.drop_index("ix_notifications_user_created", table_name="notifications")
    op.drop_index(op.f("ix_notifications_dossier_id"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_user_id"), table_name="notifications")
    op.drop_table("notifications")
