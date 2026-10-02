"""Sources des champs d'un modèle de document, vérifiées contre **son analyse** (issue #139).

Un modèle appartient à une analyse : un champ qui tire sa valeur d'un élément de l'analyse ne peut désigner qu'un
élément que cette analyse définit — une entité (extraction), un label (classification) ou un agent (synthèse). Les
relations et les champs « renseignés au fil de l'instruction » n'ont pas de définition à vérifier."""

from app.models.analyse import Analyse
from app.schemas.document_template import AnalysisSource, FieldDefinition


def definitions_of(analyse: Analyse) -> dict[str, list[str]]:
    """Noms que l'analyse définit, par type d'élément (pour proposer les choix dans l'éditeur)."""
    return {
        "entity": [e.name for e in analyse.entities],
        "classification": [label.name for label in analyse.labels],
        "synthesis": [a.name for a in analyse.agents],
    }


def unknown_sources(analyse: Analyse, fields: list[FieldDefinition]) -> list[dict[str, str]]:
    """Champs dont la source désigne un élément que l'analyse ne définit pas."""
    known = {kind: {n.casefold() for n in names} for kind, names in definitions_of(analyse).items()}
    unknown = []
    for field in fields:
        source = field.source
        if not isinstance(source, AnalysisSource) or source.element_kind not in known:
            continue
        if source.definition_name.strip().casefold() not in known[source.element_kind]:
            unknown.append(
                {"field": field.name, "element_kind": source.element_kind, "definition_name": source.definition_name}
            )
    return unknown
