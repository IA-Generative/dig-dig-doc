"""Validation humaine d'une prédiction, écrite dans l'analyse de dossier (issue #120).

Remplace l'écriture dans ``prediction_validations`` : la décision de
l'instructeur (validé, corrigé, rejeté) devient une **version d'instructeur**
de l'élément d'analyse qui porte la prédiction, avec la zone corrigée éventuelle.
Le contrat de la route ``.../predictions/{id}/validations`` ne change pas.
"""

from typing import Any

from sqlalchemy import select

from app.models.document_page import BoundingBox, DocumentPage, DocumentPrediction, PredictionValidationStatus
from app.models.dossier import DossierDocument
from app.models.dossier_analysis import (
    AnalysisElement,
    AnalysisElementKind,
    AnalysisElementVersion,
    DossierAnalysis,
    DossierAnalysisStatus,
    ElementVersionOrigin,
)
from app.repositories.dossier_analysis_repository import DossierAnalysisRepository
from app.services.analysis_builder import prediction_element_args

_REASON = {
    PredictionValidationStatus.VALIDATED: "Validée par l'instructeur",
    PredictionValidationStatus.CORRECTED: "Corrigée par l'instructeur",
    PredictionValidationStatus.REJECTED: "Rejetée par l'instructeur",
}


class AnalysisFrozenError(Exception):
    """L'analyse qui porte l'élément est figée : plus aucune modification."""


async def ensure_element(
    repository: DossierAnalysisRepository, prediction: DocumentPrediction, page: DocumentPage
) -> AnalysisElement:
    """Élément d'analyse de la prédiction, créé si besoin (prédiction déposée
    sans unité, ou dossier sans analyse) dans l'analyse courante du dossier,
    elle-même créée si le dossier n'en a pas."""
    existing = (
        await repository.db.execute(
            select(AnalysisElement).where(AnalysisElement.source_prediction_id == prediction.id)
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    dossier_id = (
        await repository.db.execute(
            select(DossierDocument.dossier_id).where(DossierDocument.id == page.dossier_document_id)
        )
    ).scalar_one()
    analysis = await repository.get_current(dossier_id) or await repository.create_analysis(dossier_id)
    return await repository.create_element(
        analysis, origin=ElementVersionOrigin.MODEL, **prediction_element_args(prediction, page)
    )


async def record_validation(
    repository: DossierAnalysisRepository,
    *,
    prediction: DocumentPrediction,
    page: DocumentPage,
    user_id: str,
    status: PredictionValidationStatus,
    corrected_value: str | None,
    bounding_box: dict[str, Any] | None,
) -> AnalysisElementVersion:
    """Ajoute la version d'instructeur correspondant à la décision.

    - validé : la valeur retenue est confirmée ;
    - corrigé : la valeur corrigée devient la version retenue ;
    - rejeté : la valeur est conservée et l'élément est signalé « à revoir »
      (le modèle d'analyse n'a pas d'état « rejeté »).

    Une zone corrigée crée toujours une nouvelle BoundingBox (jamais de mutation
    de celle de la prédiction), rattachée à la première page de la prédiction."""
    element = await ensure_element(repository, prediction, page)
    analysis = await repository.db.get(DossierAnalysis, element.analysis_id)
    if analysis is not None and analysis.status == DossierAnalysisStatus.FIGEE:
        raise AnalysisFrozenError()

    retained = await repository.db.get(AnalysisElementVersion, element.retained_version_id)
    value = dict(retained.value) if retained is not None else {}
    if status == PredictionValidationStatus.CORRECTED and corrected_value is not None:
        value = {"label" if element.kind == AnalysisElementKind.CLASSIFICATION else "value": corrected_value}

    bbox = None
    if bounding_box:
        bbox = BoundingBox(document_page_id=prediction.pages[0].id, **bounding_box)
        repository.db.add(bbox)
        await repository.db.flush()

    version = await repository.add_version(
        element,
        value=value,
        origin=ElementVersionOrigin.INSTRUCTOR,
        author_id=user_id,
        reason=_REASON[status],
        validation_status=status.value,
        bounding_box_id=bbox.id if bbox else None,
        commit=False,
    )
    if status == PredictionValidationStatus.REJECTED:
        element.needs_review = True
        element.review_reason = "Prédiction rejetée par un instructeur"
    await repository.db.commit()
    return version
