"""user_tasks table

Revision ID: f8a9b0c1d2e3
Revises: e7f8a9b0c1d2
Create Date: 2026-09-25 22:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f8a9b0c1d2e3"
down_revision: str | None = "e7f8a9b0c1d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_tasks",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False, index=True),
        sa.Column(
            "kind",
            sa.Enum(
                "TEXT_EXTRACTION",
                "CLASSIFICATION",
                "ENTITY_EXTRACTION",
                "AGENT_EXECUTION",
                "CHAT_RESPONSE",
                "HELPER_CHAT",
                "DOCUMENT_SUMMARY",
                "DOSSIER_SUMMARY",
                "ANALYSE_SUGGESTION",
                name="user_task_kind",
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("PENDING", "RUNNING", "SUCCESS", "FAILURE", name="user_task_status"),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("celery_task_id", sa.String(), nullable=True, index=True),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column(
            "target_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=True,
            index=True,
        ),
        sa.Column("target_type", sa.String(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_user_tasks_user_id_status", "user_tasks", ["user_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_user_tasks_user_id_status", table_name="user_tasks")
    op.drop_table("user_tasks")
    sa.Enum(name="user_task_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="user_task_kind").drop(op.get_bind(), checkfirst=True)
