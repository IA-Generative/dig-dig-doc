"""Tests pour les modèles de structured output et le client LLM."""

from unittest.mock import MagicMock, patch

from app.llm import (
    AnalyseSuggestion,
    ClassificationResult,
    EntityValue,
    ExtractionResult,
    LabelPrediction,
    SuggestionResult,
    suggest_analyses,
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


def test_suggestion_result_model() -> None:
    suggestions = [
        AnalyseSuggestion(analyse_id="a-1", score=0.92, rationale="Correspondance forte"),
        AnalyseSuggestion(analyse_id="a-2", score=0.45, rationale="Moins pertinent"),
    ]
    result = SuggestionResult(suggestions=suggestions)
    assert len(result.suggestions) == 2
    assert result.suggestions[0].analyse_id == "a-1"
    assert result.suggestions[0].score == 0.92
    assert result.suggestions[1].rationale == "Moins pertinent"


def test_suggest_analyses_calls_llm_with_structured_output() -> None:
    """suggest_analyses utilise beta.chat.completions.parse avec
    response_format=SuggestionResult."""
    fake_parsed = SuggestionResult(
        suggestions=[
            AnalyseSuggestion(analyse_id="a-1", score=0.9, rationale="OK"),
        ]
    )
    fake_response = MagicMock()
    fake_response.choices = [MagicMock()]
    fake_response.choices[0].message.parsed = fake_parsed

    with patch("app.llm._client") as mock_client:
        mock_client.return_value.beta.chat.completions.parse.return_value = fake_response
        result = suggest_analyses(
            dossier_summary="Dossier avec CNI",
            analyses=[{"id": "a-1", "name": "Analyse CNI"}],
        )

    assert len(result.suggestions) == 1
    assert result.suggestions[0].analyse_id == "a-1"
    call_kwargs = mock_client.return_value.beta.chat.completions.parse.call_args
    assert call_kwargs.kwargs["response_format"] == SuggestionResult
    messages = call_kwargs.kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "CNI" in messages[1]["content"]
