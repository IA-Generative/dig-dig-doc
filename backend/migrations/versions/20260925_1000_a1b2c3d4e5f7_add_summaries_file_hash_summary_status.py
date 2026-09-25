"""add document_summaries, dossier_summaries, file_hash, summary_status

Revision ID: a1b2c3d4e5f7
Revises: d44d56718aa9
Create Date: 2026-09-25 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f7"
down_revision: str | None = "d44d56718aa9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Enum type partagé par Dossier.summary_status et
    # DossierDocument.summary_status.
    summary_status_enum = sa.Enum(
        "EN_ATTENTE",
        "EN_COURS",
        "TERMINE",
        "ECHEC",
        name="summary_status",
    )
    summary_status_enum.create(op.get_bind(), checkfirst=True)

    # --- Tables de résumés (append-only, versioning) ---

    op.create_table(
        "document_summaries",
        sa.Column("dossier_document_id", sa.UUID(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["dossier_document_id"], ["dossier_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_document_summaries_dossier_document_id"),
        "document_summaries",
        ["dossier_document_id"],
        unique=False,
    )

    op.create_table(
        "dossier_summaries",
        sa.Column("dossier_id", sa.UUID(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["dossier_id"], ["dossiers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_dossier_summaries_dossier_id"),
        "dossier_summaries",
        ["dossier_id"],
        unique=False,
    )

    # --- Colonnes sur les tables existantes ---

    op.add_column(
        "dossier_documents",
        sa.Column("file_hash", sa.String(64), nullable=True),
    )
    op.create_index(
        op.f("ix_dossier_documents_file_hash"),
        "dossier_documents",
        ["file_hash"],
        unique=False,
    )
    op.add_column(
        "dossier_documents",
        sa.Column(
            "summary_status",
            sa.Enum("EN_ATTENTE", "EN_COURS", "TERMINE", "ECHEC", name="summary_status"),
            nullable=False,
            server_default="EN_ATTENTE",
        ),
    )
    op.add_column(
        "dossier_documents",
        sa.Column("summary_error", sa.Text(), nullable=True),
    )

    op.add_column(
        "dossiers",
        sa.Column(
            "summary_status",
            sa.Enum("EN_ATTENTE", "EN_COURS", "TERMINE", "ECHEC", name="summary_status"),
            nullable=False,
            server_default="EN_ATTENTE",
        ),
    )
    op.add_column(
        "dossiers",
        sa.Column("summary_error", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("dossiers", "summary_error")
    op.drop_column("dossiers", "summary_status")
    op.drop_column("dossier_documents", "summary_error")
    op.drop_column("dossier_documents", "summary_status")
    op.drop_index(op.f("ix_dossier_documents_file_hash"), table_name="dossier_documents")
    op.drop_column("dossier_documents", "file_hash")

    op.drop_index(op.f("ix_dossier_summaries_dossier_id"), table_name="dossier_summaries")
    op.drop_table("dossier_summaries")

    op.drop_index(op.f("ix_document_summaries_dossier_document_id"), table_name="document_summaries")
    op.drop_table("document_summaries")

    sa.Enum(name="summary_status").drop(op.get_bind(), checkfirst=True)
