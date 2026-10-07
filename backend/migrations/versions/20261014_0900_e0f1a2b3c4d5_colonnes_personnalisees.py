"""colonnes personnalisées du suivi (issue #173)

Revision ID: e0f1a2b3c4d5
Revises: d9e0f1a2b3c4
Create Date: 2026-10-14 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e0f1a2b3c4d5"
down_revision: str | None = "d9e0f1a2b3c4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Une valeur d'enum ne peut pas être ajoutée dans une transaction avec usage immédiat.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE versioned_field ADD VALUE IF NOT EXISTS 'CUSTOM_FIELDS'")

    op.add_column(
        "analyses",
        sa.Column("custom_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
    )
    op.add_column(
        "dossiers",
        sa.Column("custom_values", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
    )
    op.alter_column("analyses", "custom_fields", server_default=None)
    op.alter_column("dossiers", "custom_values", server_default=None)


def downgrade() -> None:
    op.drop_column("dossiers", "custom_values")
    op.drop_column("analyses", "custom_fields")
    # La valeur d'enum 'CUSTOM_FIELDS' reste : PostgreSQL ne sait pas retirer une valeur d'un enum, et les versions
    # déjà enregistrées pourraient la porter.
