"""propositions de modification de l'analyse de dossier

Revision ID: 2b3c4d5e6f7a
Revises: 1a2b3c4d5e6f
Create Date: 2026-10-01 22:25:06.405798

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "2b3c4d5e6f7a"
down_revision: str | None = "1a2b3c4d5e6f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "analysis_proposals",
        sa.Column("analysis_id", sa.UUID(), nullable=False),
        sa.Column("element_id", sa.UUID(), nullable=True),
        sa.Column(
            "kind",
            # Type déjà créé par la migration de l'analyse de dossier (1a2b3c4d5e6f).
            postgresql.ENUM(
                "CLASSIFICATION",
                "ENTITY",
                "RELATION",
                "SYNTHESIS",
                "FIELD",
                name="analysis_element_kind",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("definition_name", sa.String(), nullable=True),
        sa.Column("base_version_id", sa.UUID(), nullable=True),
        sa.Column("proposed_value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(), nullable=True),
        sa.Column("source_id", sa.UUID(), nullable=True),
        sa.Column("proposed_by", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("prompt_version", sa.String(), nullable=True),
        sa.Column(
            "status", sa.Enum("PENDING", "ACCEPTED", "MODIFIED", "REJECTED", name="proposal_status"), nullable=False
        ),
        sa.Column("decided_by", sa.String(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resulting_version_id", sa.UUID(), nullable=True),
        sa.Column("resulting_element_id", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["dossier_analyses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["base_version_id"], ["analysis_element_versions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["element_id"], ["analysis_elements.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resulting_element_id"], ["analysis_elements.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["resulting_version_id"], ["analysis_element_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_analysis_proposals_analysis_id"), "analysis_proposals", ["analysis_id"], unique=False)
    op.create_index(op.f("ix_analysis_proposals_element_id"), "analysis_proposals", ["element_id"], unique=False)
    op.create_index(op.f("ix_analysis_proposals_status"), "analysis_proposals", ["status"], unique=False)
    op.create_table(
        "analysis_proposal_events",
        sa.Column("proposal_id", sa.UUID(), nullable=False),
        sa.Column(
            "kind", sa.Enum("PROPOSED", "ACCEPTED", "MODIFIED", "REJECTED", name="proposal_event_kind"), nullable=False
        ),
        sa.Column("actor_id", sa.String(), nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("prompt_version", sa.String(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["proposal_id"], ["analysis_proposals.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_analysis_proposal_events_proposal_id"), "analysis_proposal_events", ["proposal_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_analysis_proposal_events_proposal_id"), table_name="analysis_proposal_events")
    op.drop_table("analysis_proposal_events")
    op.drop_index(op.f("ix_analysis_proposals_status"), table_name="analysis_proposals")
    op.drop_index(op.f("ix_analysis_proposals_element_id"), table_name="analysis_proposals")
    op.drop_index(op.f("ix_analysis_proposals_analysis_id"), table_name="analysis_proposals")
    op.drop_table("analysis_proposals")
    # Les types ENUM PostgreSQL ne sont pas supprimés avec leur table
    # (analysis_element_kind appartient à la migration précédente).
    op.execute("DROP TYPE IF EXISTS proposal_event_kind")
    op.execute("DROP TYPE IF EXISTS proposal_status")
