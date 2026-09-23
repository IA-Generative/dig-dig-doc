"""Unique constraint on conversations (dossier_id, user_id)

Revision ID: a1b2c3d4e5f6
Revises: 597c7128b6c2
Create Date: 2026-09-23 13:10:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "597c7128b6c2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Supprime d'abord les doublons éventuels (garde le plus ancien par
    # created_at) avant de poser la contrainte d'unicité.
    op.execute(
        """
        DELETE FROM conversations
        WHERE id NOT IN (
            SELECT DISTINCT ON (dossier_id, user_id) id
            FROM conversations
            ORDER BY dossier_id, user_id, created_at ASC
        )
        """
    )
    op.create_unique_constraint(
        "uq_conversations_dossier_id_user_id",
        "conversations",
        ["dossier_id", "user_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_conversations_dossier_id_user_id", "conversations", type_="unique")
