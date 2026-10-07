"""échéance des dossiers : date, durée par défaut et seuils de couleur par analyse (issue #172)

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-10-08 09:00:00.000000

"""

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e4f5a6b7c8d9"
down_revision: str | None = "d3e4f5a6b7c8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Seuils par défaut (voir app/services/due_date.py) : figés ici, une migration ne dépend pas du code courant.
DEFAULT_THRESHOLDS = {
    "far_color": "#18753c",
    "steps": [{"days": 30, "color": "#b34000"}, {"days": 7, "color": "#ce0500"}],
    "overdue_color": "#8a0000",
}


def upgrade() -> None:
    # Une valeur d'enum ne peut pas être ajoutée dans une transaction avec usage immédiat.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE versioned_field ADD VALUE IF NOT EXISTS 'DUE_SETTINGS'")

    op.add_column("dossiers", sa.Column("due_at", sa.Date(), nullable=True))
    op.create_index(op.f("ix_dossiers_due_at"), "dossiers", ["due_at"], unique=False)

    op.add_column("analyses", sa.Column("default_due_days", sa.Integer(), nullable=True))
    # Les analyses existantes reçoivent les seuils par défaut ; elles n'ont pas de durée par défaut
    # (aucun dossier existant ne reçoit d'échéance : on ne devine pas une date limite).
    op.add_column(
        "analyses",
        sa.Column(
            "due_thresholds",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text(f"'{json.dumps(DEFAULT_THRESHOLDS)}'::jsonb"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("analyses", "due_thresholds")
    op.drop_column("analyses", "default_due_days")
    op.drop_index(op.f("ix_dossiers_due_at"), table_name="dossiers")
    op.drop_column("dossiers", "due_at")
    # La valeur 'DUE_SETTINGS' de l'enum versioned_field est conservée (PostgreSQL ne sait pas retirer une valeur
    # d'enum) ; les versions qui l'utilisent n'ont plus d'objet.
    op.execute("DELETE FROM field_versions WHERE field = 'DUE_SETTINGS'")
