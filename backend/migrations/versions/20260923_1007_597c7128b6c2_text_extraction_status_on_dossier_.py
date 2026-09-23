"""text extraction status on dossier documents

Revision ID: 597c7128b6c2
Revises: f3ace41df805
Create Date: 2026-09-23 10:07:31.565946

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "597c7128b6c2"
down_revision: str | None = "f3ace41df805"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

text_extraction_status_enum = sa.Enum("EN_ATTENTE", "EN_COURS", "TERMINE", "ECHEC", name="text_extraction_status")


def upgrade() -> None:
    # op.add_column() ne crée pas le type ENUM Postgres tout seul
    # (contrairement à op.create_table()) - il faut le créer explicitement
    # avant de l'utiliser dans une colonne.
    text_extraction_status_enum.create(op.get_bind(), checkfirst=True)
    # nullable=True d'abord, backfill, puis contrainte NOT NULL : les
    # documents déjà en base n'ont pas de valeur pour cette nouvelle colonne.
    op.add_column("dossier_documents", sa.Column("text_extraction_status", text_extraction_status_enum, nullable=True))
    op.execute("UPDATE dossier_documents SET text_extraction_status = 'EN_ATTENTE'")
    op.alter_column("dossier_documents", "text_extraction_status", nullable=False)
    op.add_column("dossier_documents", sa.Column("text_extraction_error", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("dossier_documents", "text_extraction_error")
    op.drop_column("dossier_documents", "text_extraction_status")
    text_extraction_status_enum.drop(op.get_bind(), checkfirst=True)
