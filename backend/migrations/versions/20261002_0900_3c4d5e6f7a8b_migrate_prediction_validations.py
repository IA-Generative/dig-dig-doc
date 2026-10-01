"""migrer les validations de prédiction vers l'analyse de dossier (#120)

Les validations humaines des prédictions (``prediction_validations``) deviennent
des versions d'éléments de l'analyse de dossier (#112) :

- deux colonnes sur ``analysis_element_versions`` : ``validation_status``
  (validé / corrigé / rejeté) et ``bounding_box_id`` (zone corrigée) ;
- les prédictions qui n'ont pas encore d'élément reçoivent une **analyse de
  rattrapage** par dossier (les exécutions passées ne sont pas reconstituables) ;
- chaque validation devient une version d'instructeur, dans l'ordre
  chronologique ; la dernière devient la version retenue.

La table ``prediction_validations`` n'est ni modifiée ni supprimée (suppression
dans une migration ultérieure) : le downgrade retrouve l'ancien état. Le
comptage avant/après est vérifié : s'il diffère, la migration échoue et rien
n'est appliqué (DDL transactionnel).

Revision ID: 3c4d5e6f7a8b
Revises: 2b3c4d5e6f7a
Create Date: 2026-10-02 09:00:00.000000

"""

import json
import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3c4d5e6f7a8b"
down_revision: str | None = "2b3c4d5e6f7a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Repère des analyses créées par cette migration (utilisé par le downgrade).
BACKFILL_MARKER = "rattrapage (migration #120)"
# Repère des versions issues d'une ligne de prediction_validations : rend la
# migration idempotente (une validation déjà migrée n'est jamais recopiée).
SOURCE_TYPE = "prediction_validation"

_STATUS = {"VALIDATED": "validé", "CORRECTED": "corrigé", "REJECTED": "rejeté"}
_REASON = {
    "validé": "Validée par l'instructeur (historique migré)",
    "corrigé": "Corrigée par l'instructeur (historique migré)",
    "rejeté": "Rejetée par l'instructeur (historique migré)",
}


def upgrade() -> None:
    op.add_column("analysis_element_versions", sa.Column("validation_status", sa.String(), nullable=True))
    op.add_column("analysis_element_versions", sa.Column("bounding_box_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_analysis_element_versions_bounding_box",
        "analysis_element_versions",
        "bounding_boxes",
        ["bounding_box_id"],
        ["id"],
        ondelete="SET NULL",
    )
    backfill(op.get_bind())


def downgrade() -> None:
    bind = op.get_bind()
    # Les analyses de rattrapage partent avec leurs éléments et versions
    # (suppression en cascade) ; les versions migrées d'analyses existantes
    # sont retirées. prediction_validations n'a jamais été modifiée.
    bind.execute(sa.text("DELETE FROM dossier_analyses WHERE analyse_version = :marker"), {"marker": BACKFILL_MARKER})
    # Les pointeurs d'un élément vers une version supprimée repassent à NULL
    # (ON DELETE SET NULL) : on les recalcule sur la version restante la plus récente.
    bind.execute(sa.text("DELETE FROM analysis_element_versions WHERE source_type = :source"), {"source": SOURCE_TYPE})
    bind.execute(
        sa.text(
            "UPDATE analysis_elements e SET retained_version_id = ("
            "SELECT v.id FROM analysis_element_versions v WHERE v.element_id = e.id "
            "ORDER BY v.version_number DESC LIMIT 1) WHERE e.retained_version_id IS NULL"
        )
    )
    op.drop_constraint("fk_analysis_element_versions_bounding_box", "analysis_element_versions", type_="foreignkey")
    op.drop_column("analysis_element_versions", "bounding_box_id")
    op.drop_column("analysis_element_versions", "validation_status")


# --- Migration des données --------------------------------------------------


def _jsonb(value: dict) -> str:
    return json.dumps(value)


def backfill(connection: sa.Connection) -> dict[str, int]:
    """Crée les éléments manquants et migre les validations non encore migrées.
    Renvoie des compteurs. Idempotent : un second appel ne fait rien."""
    # Une prédiction sans aucune page (page supprimée) n'appartient plus à un
    # dossier : on ne peut pas la rattacher, ses validations sont ignorées.
    has_page = "EXISTS (SELECT 1 FROM prediction_pages pp WHERE pp.prediction_id = v.prediction_id)"
    expected = connection.execute(
        sa.text(
            f"SELECT count(*) FROM prediction_validations v WHERE {has_page} AND NOT EXISTS ("
            "SELECT 1 FROM analysis_element_versions av "
            "WHERE av.source_type = :source AND av.source_id = v.id)"
        ),
        {"source": SOURCE_TYPE},
    ).scalar_one()

    # Prédictions à traiter : sans élément, ou avec au moins une validation à migrer.
    rows = (
        connection.execute(
            sa.text(
                """
            SELECT p.id, p.kind::text AS kind, p.name, p.value, p.confidence, p.created_at,
                   p.label_definition_id, p.entity_definition_id,
                   dd.dossier_id, dp.dossier_document_id AS document_id, dp.page_number,
                   e.id AS element_id
            FROM document_predictions p
            JOIN LATERAL (
                SELECT pg.dossier_document_id, pg.page_number
                FROM prediction_pages pp JOIN document_pages pg ON pg.id = pp.document_page_id
                WHERE pp.prediction_id = p.id
                ORDER BY pg.page_number LIMIT 1
            ) dp ON TRUE
            JOIN dossier_documents dd ON dd.id = dp.dossier_document_id
            LEFT JOIN analysis_elements e ON e.source_prediction_id = p.id
            WHERE e.id IS NULL
               OR EXISTS (
                   SELECT 1 FROM prediction_validations v WHERE v.prediction_id = p.id AND NOT EXISTS (
                       SELECT 1 FROM analysis_element_versions av
                       WHERE av.source_type = :source AND av.source_id = v.id))
            ORDER BY dd.dossier_id, p.created_at, p.id
            """
            ),
            {"source": SOURCE_TYPE},
        )
        .mappings()
        .all()
    )

    stats = {"analyses": 0, "elements": 0, "versions": 0}
    backfill_analysis: dict[uuid.UUID, uuid.UUID] = {}

    for row in rows:
        element_id = row["element_id"]
        if element_id is None:
            analysis_id = backfill_analysis.get(row["dossier_id"])
            if analysis_id is None:
                analysis_id = _create_backfill_analysis(connection, row["dossier_id"])
                backfill_analysis[row["dossier_id"]] = analysis_id
                stats["analyses"] += 1
            element_id = _create_element(connection, analysis_id, row)
            stats["elements"] += 1
        stats["versions"] += _migrate_validations(connection, element_id, row)

    migrated = connection.execute(
        sa.text("SELECT count(*) FROM analysis_element_versions WHERE source_type = :source"), {"source": SOURCE_TYPE}
    ).scalar_one()
    total = connection.execute(sa.text(f"SELECT count(*) FROM prediction_validations v WHERE {has_page}")).scalar_one()
    if stats["versions"] != expected or migrated != total:
        raise RuntimeError(
            f"Migration des validations incohérente : {stats['versions']} migrée(s) pour {expected} attendue(s), "
            f"{migrated} version(s) migrée(s) au total pour {total} validation(s) en base. Rien n'est appliqué."
        )
    return stats


def _create_backfill_analysis(connection: sa.Connection, dossier_id: uuid.UUID) -> uuid.UUID:
    analysis_id = uuid.uuid4()
    # Jamais plus récente qu'une analyse existante : l'analyse courante d'un
    # dossier reste celle de sa dernière exécution.
    sequence = connection.execute(
        sa.text("SELECT COALESCE(MIN(sequence), 2) - 1 FROM dossier_analyses WHERE dossier_id = :d"),
        {"d": dossier_id},
    ).scalar_one()
    connection.execute(
        sa.text(
            "INSERT INTO dossier_analyses (id, dossier_id, sequence, status, analyse_version) "
            "VALUES (:id, :d, :seq, 'BROUILLON', :marker)"
        ),
        {"id": analysis_id, "d": dossier_id, "seq": sequence, "marker": BACKFILL_MARKER},
    )
    return analysis_id


def _create_element(connection: sa.Connection, analysis_id: uuid.UUID, row) -> uuid.UUID:
    is_label = row["kind"] == "LABEL"
    element_id, version_id = uuid.uuid4(), uuid.uuid4()
    connection.execute(
        sa.text(
            "INSERT INTO analysis_elements (id, analysis_id, kind, definition_id, definition_name, document_id, "
            "first_page_number, source_prediction_id, created_at) "
            "VALUES (:id, :a, CAST(:kind AS analysis_element_kind), :def, :name, :doc, :page, :pred, :created)"
        ),
        {
            "id": element_id,
            "a": analysis_id,
            "kind": "CLASSIFICATION" if is_label else "ENTITY",
            "def": row["label_definition_id"] if is_label else row["entity_definition_id"],
            "name": row["name"],
            "doc": row["document_id"],
            "page": row["page_number"],
            "pred": row["id"],
            "created": row["created_at"],
        },
    )
    connection.execute(
        sa.text(
            "INSERT INTO analysis_element_versions (id, element_id, version_number, value, confidence, origin, "
            "prediction_id, created_at) "
            "VALUES (:id, :el, 1, CAST(:value AS jsonb), :conf, 'MODEL', :pred, :created)"
        ),
        {
            "id": version_id,
            "el": element_id,
            "value": _jsonb({"label" if is_label else "value": row["value"]}),
            "conf": row["confidence"],
            "pred": row["id"],
            "created": row["created_at"],
        },
    )
    connection.execute(
        sa.text("UPDATE analysis_elements SET retained_version_id = :v, latest_model_version_id = :v WHERE id = :id"),
        {"v": version_id, "id": element_id},
    )
    return element_id


def _migrate_validations(connection: sa.Connection, element_id: uuid.UUID, row) -> int:
    """Ajoute une version d'instructeur par validation non encore migrée, dans
    l'ordre chronologique. La dernière devient la version retenue ; un rejet
    marque l'élément « à revoir » (le modèle n'a pas d'état « rejeté »)."""
    validations = (
        connection.execute(
            sa.text(
                "SELECT v.id, v.validator_user_id, v.status::text AS status, v.corrected_value, v.bounding_box_id, "
                "v.created_at FROM prediction_validations v WHERE v.prediction_id = :p AND NOT EXISTS ("
                "SELECT 1 FROM analysis_element_versions av WHERE av.source_type = :source AND av.source_id = v.id) "
                "ORDER BY v.created_at, v.id"
            ),
            {"p": row["id"], "source": SOURCE_TYPE},
        )
        .mappings()
        .all()
    )
    if not validations:
        return 0

    retained = (
        connection.execute(
            sa.text(
                "SELECT av.value, av.version_number FROM analysis_elements e "
                "JOIN analysis_element_versions av ON av.id = e.retained_version_id WHERE e.id = :id"
            ),
            {"id": element_id},
        )
        .mappings()
        .one()
    )
    value = retained["value"]
    number = connection.execute(
        sa.text("SELECT COALESCE(MAX(version_number), 0) FROM analysis_element_versions WHERE element_id = :id"),
        {"id": element_id},
    ).scalar_one()
    key = "label" if row["kind"] == "LABEL" else "value"

    last_version_id = None
    last_status = None
    for validation in validations:
        status = _STATUS[validation["status"]]
        if status == "corrigé" and validation["corrected_value"] is not None:
            value = {key: validation["corrected_value"]}
        number += 1
        last_version_id = uuid.uuid4()
        last_status = status
        connection.execute(
            sa.text(
                "INSERT INTO analysis_element_versions (id, element_id, version_number, value, origin, author_id, "
                "reason, source_type, source_id, validation_status, bounding_box_id, created_at) "
                "VALUES (:id, :el, :n, CAST(:value AS jsonb), 'INSTRUCTOR', :author, :reason, :source, :src_id, "
                ":status, :bbox, :created)"
            ),
            {
                "id": last_version_id,
                "el": element_id,
                "n": number,
                "value": _jsonb(value),
                "author": validation["validator_user_id"],
                "reason": _REASON[status],
                "source": SOURCE_TYPE,
                "src_id": validation["id"],
                "status": status,
                "bbox": validation["bounding_box_id"],
                "created": validation["created_at"],
            },
        )
    connection.execute(
        sa.text(
            "UPDATE analysis_elements SET retained_version_id = :v, needs_review = :review, review_reason = :reason "
            "WHERE id = :id"
        ),
        {
            "v": last_version_id,
            "review": last_status == "rejeté",
            "reason": "Prédiction rejetée par un instructeur" if last_status == "rejeté" else None,
            "id": element_id,
        },
    )
    return len(validations)
