"""statuts de dossier par analyse et date de clôture (issue #168)

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-10-07 10:00:00.000000

"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c2d3e4f5a6b7"
down_revision: str | None = "b1c2d3e4f5a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Statuts par défaut donnés à chaque analyse existante (nom, couleur, initial, final).
DEFAULT_STATUSES = [
    ("À instruire", "#6a6af4", True, False),
    ("En instruction", "#0063cb", False, False),
    ("Terminé", "#18753c", False, True),
]


def upgrade() -> None:
    # Une valeur d'enum ne peut pas être ajoutée dans une transaction avec usage immédiat.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE versioned_field ADD VALUE IF NOT EXISTS 'STATUSES'")

    op.create_table(
        "status_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analyse_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("color", sa.String(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("is_initial", sa.Boolean(), nullable=False),
        sa.Column("is_final", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["analyse_id"], ["analyses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_status_definitions_analyse_id"), "status_definitions", ["analyse_id"], unique=False)

    op.add_column("dossiers", sa.Column("workflow_status_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("dossiers", sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f("ix_dossiers_workflow_status_id"), "dossiers", ["workflow_status_id"], unique=False)
    op.create_foreign_key(
        "fk_dossiers_workflow_status_id",
        "dossiers",
        "status_definitions",
        ["workflow_status_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # Données : chaque analyse existante reçoit les statuts par défaut, et ses
    # dossiers prennent le statut initial (aucun n'est clos : closed_at reste NULL).
    bind = op.get_bind()
    statuses = sa.table(
        "status_definitions",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("analyse_id", postgresql.UUID(as_uuid=True)),
        sa.column("name", sa.String()),
        sa.column("color", sa.String()),
        sa.column("position", sa.Integer()),
        sa.column("is_initial", sa.Boolean()),
        sa.column("is_final", sa.Boolean()),
    )
    analyse_ids = [row[0] for row in bind.execute(sa.text("SELECT id FROM analyses"))]
    initial_by_analyse: dict[uuid.UUID, uuid.UUID] = {}
    for analyse_id in analyse_ids:
        for position, (name, color, is_initial, is_final) in enumerate(DEFAULT_STATUSES):
            status_id = uuid.uuid4()
            if is_initial:
                initial_by_analyse[analyse_id] = status_id
            op.execute(
                statuses.insert().values(
                    id=status_id,
                    analyse_id=analyse_id,
                    name=name,
                    color=color,
                    position=position,
                    is_initial=is_initial,
                    is_final=is_final,
                )
            )
    for analyse_id, status_id in initial_by_analyse.items():
        bind.execute(
            sa.text("UPDATE dossiers SET workflow_status_id = :status_id WHERE analyse_id = :analyse_id"),
            {"status_id": status_id, "analyse_id": analyse_id},
        )


def downgrade() -> None:
    op.drop_constraint("fk_dossiers_workflow_status_id", "dossiers", type_="foreignkey")
    op.drop_index(op.f("ix_dossiers_workflow_status_id"), table_name="dossiers")
    op.drop_column("dossiers", "closed_at")
    op.drop_column("dossiers", "workflow_status_id")
    op.drop_index(op.f("ix_status_definitions_analyse_id"), table_name="status_definitions")
    op.drop_table("status_definitions")
    # La valeur 'statuses' de l'enum versioned_field est conservée : PostgreSQL ne permet pas
    # de retirer une valeur d'enum, et les FieldVersion qui l'utilisent partent avec leurs analyses.
    op.execute("DELETE FROM field_versions WHERE field = 'STATUSES'")
