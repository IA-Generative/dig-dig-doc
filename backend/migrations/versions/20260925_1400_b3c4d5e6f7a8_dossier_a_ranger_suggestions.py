"""add suggested_analyses, suggestion_status, make analyse_id nullable

Revision ID: b3c4d5e6f7a8
Revises: a1b2c3d4e5f7
Create Date: 2026-09-25 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "b3c4d5e6f7a8"
down_revision: str | None = "a1b2c3d4e5f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Enum type pour le statut de génération des suggestions d'analyse.
    suggestion_status_enum = sa.Enum(
        "EN_ATTENTE",
        "EN_COURS",
        "TERMINE",
        "ECHEC",
        name="suggestion_status",
    )
    suggestion_status_enum.create(op.get_bind(), checkfirst=True)

    # Rendre analyse_id nullable (dossier « à ranger » sans analyse, issue #54).
    op.alter_column(
        "dossiers",
        "analyse_id",
        existing_type=sa.UUID(),
        nullable=True,
    )

    # Suggestions d'analyse générées par le LLM (JSONB : liste de
    # {analyse_id, name, score, rationale}).
    op.add_column(
        "dossiers",
        sa.Column("suggested_analyses", JSONB(), nullable=True),
    )
    op.add_column(
        "dossiers",
        sa.Column(
            "suggestion_status",
            sa.Enum("EN_ATTENTE", "EN_COURS", "TERMINE", "ECHEC", name="suggestion_status"),
            nullable=False,
            server_default="EN_ATTENTE",
        ),
    )


def downgrade() -> None:
    op.drop_column("dossiers", "suggestion_status")
    op.drop_column("dossiers", "suggested_analyses")

    # Restaurer analyse_id comme non-nullable : les dossiers existants sans
    # analyse (cas « à ranger ») doivent être rattachés manuellement avant
    # le downgrade.
    op.alter_column(
        "dossiers",
        "analyse_id",
        existing_type=sa.UUID(),
        nullable=False,
    )

    sa.Enum(name="suggestion_status").drop(op.get_bind(), checkfirst=True)
