"""accès aux dossiers par groupe (issue #177)

Revision ID: d9e0f1a2b3c4
Revises: c8d9e0f1a2b3
Create Date: 2026-10-13 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "d9e0f1a2b3c4"
down_revision: str | None = "c8d9e0f1a2b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Les dossiers existants passent « selon l'analyse » : personne ne perd d'accès à la mise en production.
    op.add_column("dossiers", sa.Column("visibility", sa.String(), nullable=False, server_default="analyse"))
    op.alter_column("dossiers", "visibility", server_default=None)
    op.create_table(
        "dossier_group_access",
        sa.Column("dossier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("keycloak_group", sa.String(), nullable=False),
        sa.Column("granted_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["dossier_id"], ["dossiers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("dossier_id", "keycloak_group"),
    )
    op.create_index("ix_dossier_group_access_group", "dossier_group_access", ["keycloak_group"], unique=False)
    op.add_column(
        "app_users",
        sa.Column("groups", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
    )
    op.add_column("app_users", sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.alter_column("app_users", "groups", server_default=None)
    op.alter_column("app_users", "is_admin", server_default=None)


def downgrade() -> None:
    op.drop_column("app_users", "is_admin")
    op.drop_column("app_users", "groups")
    op.drop_index("ix_dossier_group_access_group", table_name="dossier_group_access")
    op.drop_table("dossier_group_access")
    op.drop_column("dossiers", "visibility")
