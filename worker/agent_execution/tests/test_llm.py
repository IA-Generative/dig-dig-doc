"""Tests pour les modèles de structured output et le client LLM."""

from app.llm import (
    ClassificationResult,
    EntityValue,
    ExtractionResult,
    LabelPrediction,
)


def test_label_prediction_model() -> None:
    pred = LabelPrediction(label_name="CNI", confidence=0.95, reasoning="Photo visible")
    assert pred.label_name == "CNI"
    assert pred.confidence == 0.95
    assert pred.reasoning == "Photo visible"


def test_classification_result_model() -> None:
    pred = LabelPrediction(label_name="Facture", confidence=0.8)
    result = ClassificationResult(prediction=pred)
    assert result.prediction.label_name == "Facture"
    assert result.prediction.confidence == 0.8


def test_entity_value_model() -> None:
    entity = EntityValue(
        entity_name="montant_total",
        value="42.50 €",
        confidence=0.9,
        page_numbers=[1, 2],
    )
    assert entity.entity_name == "montant_total"
    assert entity.value == "42.50 €"
    assert entity.confidence == 0.9
    assert entity.page_numbers == [1, 2]


def test_extraction_result_model() -> None:
    entities = [
        EntityValue(entity_name="nom", value="Dupont", confidence=0.95, page_numbers=[1]),
        EntityValue(entity_name="date", value="2024-01-15", confidence=0.88, page_numbers=[1]),
    ]
    result = ExtractionResult(entities=entities)
    assert len(result.entities) == 2
    assert result.entities[0].entity_name == "nom"
    assert result.entities[1].entity_name == "date"


def test_extraction_result_empty() -> None:
    result = ExtractionResult()
    assert result.entities == []
