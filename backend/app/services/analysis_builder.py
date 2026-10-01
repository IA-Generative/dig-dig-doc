"""Alimentation de l'analyse de dossier pendant l'exécution (issue #125, parent #113).

Le pipeline existant (worker -> API interne) continue de fonctionner tel quel ;
ce module en tire l'analyse de dossier au fil de l'eau :

- chaque prédiction déposée avec une unité devient un **élément** (version de
  provenance « modèle », lien vers la prédiction - idempotent grâce à
  l'unicité sur la prédiction source) ;
- chaque agent terminé produit une **unité** et un élément « synthèse » ;
- une unité que le worker n'a pas pu terminer est marquée en échec quand son
  étape échoue.

Tout est tolérant : un dossier sans analyse (créé avant #125, exécution déjà
en cours) continue de fonctionner, rien n'est écrit.
"""

import hashlib
import json
import logging
import uuid

from sqlalchemy import select

from app.db import async_session_factory
from app.models.analyse import Agent
from app.models.document_page import DocumentPage, DocumentPrediction, PredictionKind
from app.models.dossier import Dossier, ExecutionStep, ExecutionStepKind, ExecutionStepStatus
from app.models.dossier_analysis import (
    AnalysisElement,
    AnalysisElementKind,
    AnalysisUnit,
    AnalysisUnitKind,
    AnalysisUnitStatus,
    DossierAnalysis,
    ElementVersionOrigin,
)
from app.repositories.dossier_analysis_repository import DossierAnalysisRepository
from app.services import analysis_carryover

logger = logging.getLogger(__name__)

# Version du pipeline pour les empreintes d'agents : à incrémenter quand la
# logique d'un agent change de façon à modifier ses résultats (le worker a la
# sienne pour les empreintes de classification et d'extraction).
AGENT_PIPELINE_VERSION = "pipeline-1"

_STEP_TO_UNIT_KIND = {
    ExecutionStepKind.CLASSIFICATION: AnalysisUnitKind.CLASSIFICATION,
    ExecutionStepKind.EXTRACTION: AnalysisUnitKind.EXTRACTION,
    ExecutionStepKind.AGENT: AnalysisUnitKind.AGENT,
}


def prediction_element_args(prediction: DocumentPrediction, page: DocumentPage) -> dict:
    """Champs de l'élément d'analyse correspondant à une prédiction (classification
    ou entité) : type, valeur, définition, document, première page, source."""
    if prediction.kind == PredictionKind.LABEL:
        kind, value, definition_id = (
            AnalysisElementKind.CLASSIFICATION,
            {"label": prediction.value},
            prediction.label_definition_id,
        )
    else:
        kind, value, definition_id = (
            AnalysisElementKind.ENTITY,
            {"value": prediction.value},
            prediction.entity_definition_id,
        )
    return {
        "kind": kind,
        "value": value,
        "definition_id": definition_id,
        "definition_name": prediction.name,
        "document_id": page.dossier_document_id,
        "first_page_number": page.page_number,
        "source_prediction_id": prediction.id,
        "confidence": prediction.confidence,
    }


async def record_prediction(unit_id: uuid.UUID, prediction_id: uuid.UUID, page_id: uuid.UUID) -> None:
    """Crée l'élément d'une prédiction déposée dans une unité, dans **sa propre
    session** : un échec est journalisé et n'affecte jamais le dépôt de la
    prédiction (déjà enregistré) ni la session de la requête."""
    try:
        async with async_session_factory() as session:
            repository = DossierAnalysisRepository(session)
            unit = await repository.get_unit(unit_id)
            prediction = await session.get(DocumentPrediction, prediction_id)
            page = await session.get(DocumentPage, page_id)
            if unit is not None and prediction is not None and page is not None:
                await _create_element_from_prediction(repository, unit, prediction, page)
    except Exception:
        logger.exception("Analyse de dossier : échec de création de l'élément de la prédiction %s", prediction_id)


async def _create_element_from_prediction(
    repository: DossierAnalysisRepository,
    unit: AnalysisUnit,
    prediction: DocumentPrediction,
    page: DocumentPage,
) -> AnalysisElement | None:
    """Renvoie None si l'élément existe déjà (dépôt rejoué) ou si l'analyse de
    l'unité n'existe plus."""
    existing = await repository.db.execute(
        select(AnalysisElement).where(AnalysisElement.source_prediction_id == prediction.id)
    )
    if existing.scalar_one_or_none() is not None:
        return None
    analysis = await repository.db.get(DossierAnalysis, unit.analysis_id)
    if analysis is None:
        return None
    return await repository.create_element(
        analysis,
        origin=ElementVersionOrigin.MODEL,
        unit=unit,
        **prediction_element_args(prediction, page),
    )


async def record_step_result(step_id: uuid.UUID) -> None:
    """À la fin d'une étape : unité et synthèse d'un agent, unités ouvertes
    d'une étape en échec. Sans effet si le dossier n'a pas d'analyse. Dans
    **sa propre session** : un échec est journalisé et ne gêne pas l'étape."""
    try:
        async with async_session_factory() as session:
            step = await session.get(ExecutionStep, step_id)
            if step is not None:
                await _record_step_result(DossierAnalysisRepository(session), step)
    except Exception:
        logger.exception("Analyse de dossier : échec de l'enregistrement de l'étape %s", step_id)


async def _record_step_result(repository: DossierAnalysisRepository, step: ExecutionStep) -> None:
    analysis = await repository.get_current(step.dossier_id)
    if analysis is None:
        return
    unit_kind = _STEP_TO_UNIT_KIND[step.kind]
    if step.kind == ExecutionStepKind.AGENT:
        await _record_agent_step(repository, analysis, step)
    elif step.status == ExecutionStepStatus.ECHEC:
        await repository.close_open_units(analysis.id, unit_kind, AnalysisUnitStatus.ECHEC)
    elif step.status == ExecutionStepStatus.TERMINE:
        # Relance incrémentale (#119) : valeurs validées des unités recalculées,
        # puis éléments ajoutés à la main et relations quand les deux étapes ont fini.
        await analysis_carryover.carry_over_apports(repository, analysis, unit_kind)
        if await analysis_carryover.classification_and_extraction_done(repository, step.dossier_id):
            await analysis_carryover.carry_over_manual_elements(repository, analysis)


async def _record_agent_step(
    repository: DossierAnalysisRepository, analysis: DossierAnalysis, step: ExecutionStep
) -> None:
    if step.status == ExecutionStepStatus.EN_COURS:
        return
    succeeded = step.status == ExecutionStepStatus.TERMINE
    unit = await repository.find_agent_unit(analysis.id, step.id)
    if unit is None:
        unit = await repository.create_unit(
            analysis.id,
            kind=AnalysisUnitKind.AGENT,
            description={"step_id": str(step.id), "label": step.label},
            input_fingerprint=await agent_fingerprint(repository, analysis, step),
            status=AnalysisUnitStatus.TERMINE if succeeded else AnalysisUnitStatus.ECHEC,
        )
    if succeeded and step.output:
        already = await repository.db.execute(
            select(AnalysisElement.id).where(
                AnalysisElement.unit_id == unit.id, AnalysisElement.kind == AnalysisElementKind.SYNTHESIS
            )
        )
        if already.first() is None:
            await repository.create_element(
                analysis,
                kind=AnalysisElementKind.SYNTHESIS,
                value={"text": step.output},
                origin=ElementVersionOrigin.MODEL,
                unit=unit,
                definition_name=step.label,
            )


async def agent_fingerprint(
    repository: DossierAnalysisRepository, analysis: DossierAnalysis, step: ExecutionStep
) -> str | None:
    """Empreinte des entrées d'un agent : sa configuration (prompt, outils,
    modèle) et les empreintes des unités de classification et d'extraction de
    l'analyse, qu'il lit. Une synthèse dépend de ce qu'elle lit : si une de ces
    unités change, l'empreinte change. None si l'agent n'est pas retrouvé."""
    dossier = await repository.db.get(Dossier, step.dossier_id)
    if dossier is None or dossier.analyse_id is None:
        return None
    agent = (
        (
            await repository.db.execute(
                select(Agent).where(Agent.analyse_id == dossier.analyse_id, Agent.name == step.label)
            )
        )
        .scalars()
        .first()
    )
    if agent is None:
        return None
    upstream: list[str] = []
    for kind in (AnalysisUnitKind.CLASSIFICATION, AnalysisUnitKind.EXTRACTION):
        upstream.extend(await _unit_fingerprints(repository, analysis.id, kind))
    upstream.sort()
    payload = {
        "unit": "agent",
        "pipeline": AGENT_PIPELINE_VERSION,
        "name": agent.name,
        "prompt": agent.prompt,
        "tools": sorted(agent.tools or []),
        "model": agent.model,
        "upstream": upstream,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def _unit_fingerprints(repository: DossierAnalysisRepository, analysis_id: uuid.UUID, kind: AnalysisUnitKind):
    result = await repository.db.execute(
        select(AnalysisUnit.input_fingerprint).where(
            AnalysisUnit.analysis_id == analysis_id,
            AnalysisUnit.kind == kind,
            AnalysisUnit.input_fingerprint.is_not(None),
        )
    )
    return list(result.scalars().all())
