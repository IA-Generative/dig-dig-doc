"""référence lisible des dossiers (issue #173)

Revision ID: a6b7c8d9e0f1
Revises: f5a6b7c8d9e0
Create Date: 2026-10-10 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a6b7c8d9e0f1"
down_revision: str | None = "f5a6b7c8d9e0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Les dossiers existants reçoivent chacun un numéro à l'ajout de la colonne.
    op.add_column("dossiers", sa.Column("ref_number", sa.BigInteger(), sa.Identity(), nullable=False))
    op.create_unique_constraint("uq_dossiers_ref_number", "dossiers", ["ref_number"])


def downgrade() -> None:
    op.drop_constraint("uq_dossiers_ref_number", "dossiers", type_="unique")
    op.drop_column("dossiers", "ref_number")
