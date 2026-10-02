"""modèles de document : un modèle appartient à une analyse

Revision ID: a0b1c2d3e4f5
Revises: 9c0d1e2f3a4b
Create Date: 2026-10-02 21:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a0b1c2d3e4f5"
down_revision: str | None = "9c0d1e2f3a4b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Nullable : un modèle créé avant ce rattachement n'a pas d'analyse (aucune ne peut être devinée) ;
    # il n'est proposé à aucun dossier. L'API exige l'analyse pour tout nouveau modèle.
    op.add_column("document_templates", sa.Column("analyse_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_document_templates_analyse_id", "document_templates", "analyses", ["analyse_id"], ["id"], ondelete="CASCADE"
    )
    op.create_index(op.f("ix_document_templates_analyse_id"), "document_templates", ["analyse_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_document_templates_analyse_id"), table_name="document_templates")
    op.drop_constraint("fk_document_templates_analyse_id", "document_templates", type_="foreignkey")
    op.drop_column("document_templates", "analyse_id")
