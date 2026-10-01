"""Relance incrémentale de l'analyse de dossier (issue #119, parent #106).

Relancer un dossier crée une nouvelle analyse qui **ne recalcule que ce dont les
entrées ont changé**. Il n'y a **aucun appariement** entre analyses : on compare
les **empreintes d'unités** (#126).

- **Unité inchangée** (même type, même empreinte, terminée dans l'analyse
  précédente) : l'unité et tous ses éléments, avec toutes leurs versions, sont
  **copiés** dans la nouvelle analyse. Aucun appel au LLM.
- **Unité modifiée ou nouvelle** : le worker la calcule normalement. Les éléments
  de l'ancienne unité qui portent une **valeur validée par un instructeur** sont
  conservés et signalés « à revoir » ; les autres sont simplement remplacés.
- Les éléments **ajoutés à la main** et les **relations** sont repris (les
  relations dont une extrémité n'existe plus dans la nouvelle analyse ne le sont
  pas : ce qu'elles relient a disparu).

Les copies gardent un lien vers l'élément et la version d'origine
(``origin_element_id``, ``origin_version_id``). La provenance d'une version
copiée reste celle d'origine pour un instructeur (sa décision, son auteur, son
motif) ; une version produite par le modèle devient « reprise » (résultat d'une
exécution précédente, pas de celle-ci). ``source_prediction_id`` n'est pas
copié : il est unique et reste porté par l'élément d'origine.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.dossier import DossierDocument, ExecutionStep, ExecutionStepKind, ExecutionStepStatus
from app.models.dossier_analysis import (
    AnalysisElement,
    AnalysisElementKind,
    AnalysisElementVersion,
    AnalysisUnit,
    AnalysisUnitKind,
    AnalysisUnitStatus,
    DossierAnalysis,
    ElementVersionOrigin,
)
from app.repositories.dossier_analysis_repository import DossierAnalysisRepository

REVIEW_REASON = (
    "Les entrées de cette unité ont changé depuis la validation (texte des pages, définition, prompt ou modèle) : "
    "la valeur validée est conservée, à revoir."
)
UNTRACKED_REVIEW_REASON = (
    "Valeur validée dans une exécution dont les entrées ne sont pas suivies : conservée, à revoir."
)
SYNTHESIS_STALE_REASON = "Un élément qu'elle lit a été corrigé : à régénérer."

_REUSABLE_KINDS = (AnalysisUnitKind.CLASSIFICATION, AnalysisUnitKind.EXTRACTION)


@dataclass
class ReusedUnit:
    unit: AnalysisUnit
    # (nom de la définition, valeur produite par le modèle) des entités reprises :
    # le worker en amorce la fusion des doublons entre lots (#126).
    entities: list[tuple[str, str]]


async def _elements(repository: DossierAnalysisRepository, *conditions) -> list[AnalysisElement]:
    result = await repository.db.execute(
        select(AnalysisElement)
        .options(selectinload(AnalysisElement.versions))
        .where(*conditions)
        .order_by(AnalysisElement.created_at, AnalysisElement.id)
        .execution_options(populate_existing=True)
    )
    return list(result.scalars().all())


def _remap_relation(value: dict, mapping: dict[uuid.UUID, uuid.UUID]) -> dict | None:
    """Valeur d'une relation avec ses extrémités remplacées par leurs copies, ou
    None si une extrémité n'a pas été reprise."""
    try:
        source = mapping[uuid.UUID(str(value["source_element_id"]))]
        target = mapping[uuid.UUID(str(value["target_element_id"]))]
    except (KeyError, ValueError):
        return None
    return {**value, "source_element_id": str(source), "target_element_id": str(target)}


async def copy_element(
    repository: DossierAnalysisRepository,
    source: AnalysisElement,
    analysis_id: uuid.UUID,
    *,
    unit_id: uuid.UUID | None,
    needs_review: bool | None = None,
    review_reason: str | None = None,
    relation_mapping: dict[uuid.UUID, uuid.UUID] | None = None,
) -> AnalysisElement | None:
    """Copie un élément et toutes ses versions dans une autre analyse (sans valider
    la transaction). Les pointeurs « version retenue » et « dernière version du
    modèle » sont recalculés sur les copies. Renvoie None pour une relation dont
    une extrémité n'est pas reprise."""
    db = repository.db
    values: dict[uuid.UUID, dict] = {}
    for version in source.versions:
        value = version.value
        if source.kind == AnalysisElementKind.RELATION:
            value = _remap_relation(value, relation_mapping or {})
            if value is None:
                return None
        values[version.id] = value

    flagged = source.needs_review if needs_review is None else needs_review
    element = AnalysisElement(
        analysis_id=analysis_id,
        unit_id=unit_id,
        kind=source.kind,
        definition_id=source.definition_id,
        definition_name=source.definition_name,
        document_id=source.document_id,
        first_page_number=source.first_page_number,
        origin_element_id=source.id,
        needs_review=flagged,
        review_reason=(review_reason if needs_review is not None else source.review_reason) if flagged else None,
    )
    db.add(element)
    await db.flush()

    copies: dict[uuid.UUID, AnalysisElementVersion] = {}
    for version in source.versions:
        copy = AnalysisElementVersion(
            element_id=element.id,
            version_number=version.version_number,
            value=values[version.id],
            confidence=version.confidence,
            # Une valeur d'instructeur reste la sienne ; un résultat du modèle devient
            # « reprise » (il vient d'une exécution précédente).
            origin=(
                ElementVersionOrigin.CARRIED_OVER if version.origin == ElementVersionOrigin.MODEL else version.origin
            ),
            prediction_id=version.prediction_id,
            author_id=version.author_id,
            reason=version.reason,
            source_type=version.source_type,
            source_id=version.source_id,
            origin_version_id=version.id,
            validation_status=version.validation_status,
            bounding_box_id=version.bounding_box_id,
        )
        db.add(copy)
        copies[version.id] = copy
    await db.flush()
    # created_at d'origine conservé (l'historique garde ses dates) ; renvois de
    # restauration repointés vers les copies.
    for version in source.versions:
        copy = copies[version.id]
        copy.created_at = version.created_at
        if version.restored_from_version_id in copies:
            copy.restored_from_version_id = copies[version.restored_from_version_id].id
    element.retained_version_id = (
        copies[source.retained_version_id].id if source.retained_version_id in copies else None
    )
    element.latest_model_version_id = (
        copies[source.latest_model_version_id].id if source.latest_model_version_id in copies else None
    )
    await db.flush()
    return element


async def _already_used_sources(repository: DossierAnalysisRepository, analysis_id: uuid.UUID) -> set[uuid.UUID]:
    result = await repository.db.execute(
        select(AnalysisUnit.source_unit_id).where(
            AnalysisUnit.analysis_id == analysis_id, AnalysisUnit.source_unit_id.is_not(None)
        )
    )
    return set(result.scalars().all())


async def _find_previous_unit(
    repository: DossierAnalysisRepository,
    analysis: DossierAnalysis,
    kind: AnalysisUnitKind,
    fingerprint: str,
) -> AnalysisUnit | None:
    """Unité terminée de l'analyse précédente, de même type et de même empreinte,
    pas encore reprise par une autre unité de la nouvelle analyse (deux pages
    identiques reprennent chacune une unité distincte)."""
    if analysis.previous_analysis_id is None:
        return None
    taken = await _already_used_sources(repository, analysis.id)
    result = await repository.db.execute(
        select(AnalysisUnit)
        .where(
            AnalysisUnit.analysis_id == analysis.previous_analysis_id,
            AnalysisUnit.kind == kind,
            AnalysisUnit.input_fingerprint == fingerprint,
            AnalysisUnit.status == AnalysisUnitStatus.TERMINE,
        )
        .order_by(AnalysisUnit.created_at, AnalysisUnit.id)
    )
    return next((unit for unit in result.scalars().all() if unit.id not in taken), None)


async def reuse_unit(
    repository: DossierAnalysisRepository,
    analysis: DossierAnalysis,
    *,
    kind: AnalysisUnitKind,
    description: dict,
    fingerprint: str,
) -> ReusedUnit | None:
    """Reprend une unité inchangée de l'analyse précédente : la copie, ainsi que
    tous ses éléments, dans la nouvelle analyse. None si elle ne peut pas l'être
    (le worker la calcule alors)."""
    if kind not in _REUSABLE_KINDS:
        return None
    previous = await _find_previous_unit(repository, analysis, kind, fingerprint)
    if previous is None:
        return None
    unit = AnalysisUnit(
        analysis_id=analysis.id,
        kind=kind,
        description=description,
        status=AnalysisUnitStatus.TERMINE,
        input_fingerprint=fingerprint,
        element_count=0,
        source_unit_id=previous.id,
    )
    repository.db.add(unit)
    await repository.db.flush()

    entities: list[tuple[str, str]] = []
    count = 0
    for source in await _elements(repository, AnalysisElement.unit_id == previous.id):
        copy = await copy_element(repository, source, analysis.id, unit_id=unit.id)
        if copy is None:
            continue
        count += 1
        if source.kind == AnalysisElementKind.ENTITY:
            model_version = next((v for v in source.versions if v.id == source.latest_model_version_id), None)
            if model_version is not None:
                entities.append((source.definition_name or "", str(model_version.value.get("value", ""))))
    unit.element_count = count
    await repository.db.commit()
    return ReusedUnit(unit=unit, entities=entities)


async def reuse_agent_unit(
    repository: DossierAnalysisRepository,
    analysis: DossierAnalysis,
    step: ExecutionStep,
    fingerprint: str,
) -> tuple[AnalysisUnit, str] | None:
    """Reprend la synthèse d'un agent dont l'empreinte (configuration + ce qu'il
    lit) est inchangée. Renvoie la nouvelle unité et le texte de la synthèse."""
    previous = await _find_previous_unit(repository, analysis, AnalysisUnitKind.AGENT, fingerprint)
    if previous is None:
        return None
    sources = await _elements(
        repository, AnalysisElement.unit_id == previous.id, AnalysisElement.kind == AnalysisElementKind.SYNTHESIS
    )
    if not sources:
        return None
    unit = AnalysisUnit(
        analysis_id=analysis.id,
        kind=AnalysisUnitKind.AGENT,
        description={"step_id": str(step.id), "label": step.label},
        status=AnalysisUnitStatus.TERMINE,
        input_fingerprint=fingerprint,
        element_count=0,
        source_unit_id=previous.id,
    )
    repository.db.add(unit)
    await repository.db.flush()
    text = ""
    for source in sources:
        copy = await copy_element(repository, source, analysis.id, unit_id=unit.id)
        if copy is not None:
            unit.element_count += 1
            retained = next((v for v in source.versions if v.id == source.retained_version_id), None)
            text = text or str((retained.value if retained else {}).get("text", ""))
    await repository.db.commit()
    return unit, text


async def _carried_sources(repository: DossierAnalysisRepository, analysis_id: uuid.UUID) -> dict[uuid.UUID, uuid.UUID]:
    """Éléments déjà repris dans l'analyse : élément d'origine -> copie."""
    result = await repository.db.execute(
        select(AnalysisElement.origin_element_id, AnalysisElement.id).where(
            AnalysisElement.analysis_id == analysis_id, AnalysisElement.origin_element_id.is_not(None)
        )
    )
    return {origin: copy for origin, copy in result.all()}


def _has_instructor_value(element: AnalysisElement) -> bool:
    retained = next((v for v in element.versions if v.id == element.retained_version_id), None)
    return retained is not None and retained.origin == ElementVersionOrigin.INSTRUCTOR


async def carry_over_apports(
    repository: DossierAnalysisRepository, analysis: DossierAnalysis, kind: AnalysisUnitKind
) -> int:
    """Conserve, « à revoir », les valeurs validées par un instructeur dans les
    unités de l'analyse précédente qui n'ont **pas** été reprises (leurs entrées
    ont changé, ou elles n'existent plus) : la nouvelle valeur du modèle est
    produite à côté, l'instructeur confirme ou corrige. Les éléments sans apport
    d'instructeur ne sont pas conservés : le nouveau calcul les remplace.

    Une unité dont le document n'existe plus n'est pas reprise (ses éléments
    restent visibles dans l'analyse précédente). Idempotent."""
    if analysis.previous_analysis_id is None:
        return 0
    reused = await _already_used_sources(repository, analysis.id)
    carried = await _carried_sources(repository, analysis.id)
    units = (
        (
            await repository.db.execute(
                select(AnalysisUnit).where(
                    AnalysisUnit.analysis_id == analysis.previous_analysis_id, AnalysisUnit.kind == kind
                )
            )
        )
        .scalars()
        .all()
    )
    count = 0
    for unit in units:
        if unit.id in reused:
            continue
        document_id = (unit.description or {}).get("document_id")
        if document_id and not await _document_exists(repository, document_id):
            continue
        for source in await _elements(repository, AnalysisElement.unit_id == unit.id):
            if source.id in carried or not _has_instructor_value(source):
                continue
            copy = await copy_element(
                repository, source, analysis.id, unit_id=None, needs_review=True, review_reason=REVIEW_REASON
            )
            if copy is not None:
                carried[source.id] = copy.id
                count += 1
    await repository.db.commit()
    return count


async def _document_exists(repository: DossierAnalysisRepository, document_id: str) -> bool:
    try:
        key = uuid.UUID(str(document_id))
    except ValueError:
        return False
    return (
        await repository.db.execute(select(DossierDocument.id).where(DossierDocument.id == key))
    ).first() is not None


async def carry_over_manual_elements(repository: DossierAnalysisRepository, analysis: DossierAnalysis) -> int:
    """Reprend les éléments ajoutés à la main (sans unité), puis les relations
    dont les deux extrémités ont été reprises. À appeler quand la classification
    et l'extraction ont terminé : les copies dont dépendent les relations
    existent alors. Idempotent."""
    if analysis.previous_analysis_id is None:
        return 0
    carried = await _carried_sources(repository, analysis.id)
    previous = await _elements(
        repository, AnalysisElement.analysis_id == analysis.previous_analysis_id, AnalysisElement.unit_id.is_(None)
    )
    count = 0
    for source in previous:
        if source.kind == AnalysisElementKind.RELATION or source.id in carried:
            continue
        if source.source_prediction_id is not None:
            # Résultat du modèle sans unité (exécution antérieure au suivi par unités,
            # ou analyse de rattrapage de la migration #120) : on ne sait pas si ses
            # entrées ont changé. Sans apport d'instructeur, le nouveau calcul le
            # remplace ; avec, la valeur validée est conservée « à revoir ».
            if not _has_instructor_value(source):
                continue
            copy = await copy_element(
                repository, source, analysis.id, unit_id=None, needs_review=True, review_reason=UNTRACKED_REVIEW_REASON
            )
        else:
            copy = await copy_element(repository, source, analysis.id, unit_id=None)
        if copy is not None:
            carried[source.id] = copy.id
            count += 1
    for source in previous:
        if source.kind != AnalysisElementKind.RELATION or source.id in carried:
            continue
        copy = await copy_element(repository, source, analysis.id, unit_id=None, relation_mapping=carried)
        if copy is not None:
            carried[source.id] = copy.id
            count += 1
    await repository.db.commit()
    return count


async def classification_and_extraction_done(repository: DossierAnalysisRepository, dossier_id: uuid.UUID) -> bool:
    """Les étapes de classification et d'extraction du dossier sont-elles terminées ?"""
    steps = (
        (
            await repository.db.execute(
                select(ExecutionStep).where(
                    ExecutionStep.dossier_id == dossier_id,
                    ExecutionStep.kind.in_([ExecutionStepKind.CLASSIFICATION, ExecutionStepKind.EXTRACTION]),
                )
            )
        )
        .scalars()
        .all()
    )
    return bool(steps) and all(step.status != ExecutionStepStatus.EN_COURS for step in steps)
