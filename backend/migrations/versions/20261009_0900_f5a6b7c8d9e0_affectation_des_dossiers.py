"""affectation des dossiers et annuaire local des personnes (issue #173)

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-10-09 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f5a6b7c8d9e0"
down_revision: str | None = "e4f5a6b7c8d9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "app_users",
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False, server_default=""),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.add_column("dossiers", sa.Column("assignee_id", sa.String(), nullable=True))
    op.add_column("dossiers", sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        "fk_dossiers_assignee_id_app_users", "dossiers", "app_users", ["assignee_id"], ["user_id"], ondelete="SET NULL"
    )
    op.create_index(op.f("ix_dossiers_assignee_id"), "dossiers", ["assignee_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_dossiers_assignee_id"), table_name="dossiers")
    op.drop_constraint("fk_dossiers_assignee_id_app_users", "dossiers", type_="foreignkey")
    op.drop_column("dossiers", "assigned_at")
    op.drop_column("dossiers", "assignee_id")
    op.drop_table("app_users")
