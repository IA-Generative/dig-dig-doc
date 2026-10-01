"""Tests des brouillons de document (issue #140)."""

import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.db import async_session_factory
from app.models.document_draft import FieldEventKind
from app.models.dossier_analysis import (
    AnalysisElement,
    AnalysisElementKind,
    DossierAnalysis,
    DossierAnalysisStatus,
    ElementVersionOrigin,
)
from app.repositories.document_draft_repository import (
    DocumentDraftRepository,
    ValidatedFieldError,
    template_definitions,
)
from app.repositories.document_template_repository import DocumentTemplateRepository
from app.repositories.dossier_analysis_repository import DossierAnalysisRepository
from app.schemas.document_template import FieldDefinition

RUN = uuid.uuid4().hex[:8]


def run(client: TestClient, work: Callable[[Any], Awaitable[Any]]) -> Any:
    """Exécute du code asynchrone avec une session, dans la boucle d'événements du client de test."""

    async def runner() -> Any:
        async with async_session_factory() as session:
            return await work(session)

    return client.portal.call(runner)


def field(name: str, source: dict[str, Any] | None = None, **extra: Any) -> dict[str, Any]:
    return {"name": name, "label": name.capitalize(), "source": source or {"kind": "instruction"}, **extra}


def entity(definition_name: str) -> dict[str, Any]:
    return {"kind": "analysis", "element_kind": "entity", "definition_name": definition_name}


def meta(key: str) -> dict[str, Any]:
    return {"kind": "dossier_metadata", "key": key}


def make_template(client: TestClient, fields: list[dict[str, Any]], name: str = "Décision") -> str:
    definitions = [FieldDefinition.model_validate(f) for f in fields]

    async def create(session: Any) -> str:
        template = await DocumentTemplateRepository(session).create(
            user_id="admin",
            name=f"{name} {uuid.uuid4().hex[:8]}",
            description="",
            generation_instructions="",
            fields=definitions,
            placeholders=[d.name for d in definitions],
            file_key_for=lambda tid: f"document-templates/{tid}/v1.odt",
            file_name="m.odt",
            file_size=1,
        )
        return str(template.id)

    return run(client, create)


def make_dossier(client: TestClient) -> tuple[str, DossierAnalysis]:
    analyse_id = client.post("/api/analyses", json={"name": "Analyse doc", "description": "t"}).json()["id"]
    dossier_id = client.post("/api/dossiers", json={"name": f"Dossier {RUN}", "analyse_id": analyse_id}).json()["id"]
    analysis = run(client, lambda s: DossierAnalysisRepository(s).create_analysis(uuid.UUID(dossier_id)))
    return dossier_id, analysis


def add_element(
    client: TestClient,
    analysis: DossierAnalysis,
    kind: AnalysisElementKind,
    name: str,
    value: dict[str, Any],
    page: int | None = 1,
) -> AnalysisElement:
    return run(
        client,
        lambda s: DossierAnalysisRepository(s).create_element(
            analysis,
            kind=kind,
            value=value,
            definition_name=name,
            first_page_number=page,
            origin=ElementVersionOrigin.MODEL,
        ),
    )


def add_entity(client: TestClient, analysis: DossierAnalysis, name: str, value: str, page: int | None = 1):
    return add_element(client, analysis, AnalysisElementKind.ENTITY, name, {"value": value}, page)


def create_draft(client: TestClient, dossier_id: str, template_id: str, **body: Any) -> dict[str, Any]:
    response = client.post(f"/api/dossiers/{dossier_id}/document-drafts", json={"template_id": template_id, **body})
    assert response.status_code == 201, response.text
    return response.json()


def url(dossier_id: str, draft_id: str, suffix: str = "") -> str:
    return f"/api/dossiers/{dossier_id}/document-drafts/{draft_id}{suffix}"


def by_name(draft: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {f["name"]: f for f in draft["fields"]}


def element_fields(client: TestClient, analysis: DossierAnalysis, name: str) -> list[AnalysisElement]:
    async def fetch(session: Any) -> list[AnalysisElement]:
        from sqlalchemy import select

        rows = await session.execute(
            select(AnalysisElement).where(
                AnalysisElement.analysis_id == analysis.id,
                AnalysisElement.kind == AnalysisElementKind.FIELD,
                AnalysisElement.definition_name == name,
            )
        )
        return list(rows.scalars())

    return run(client, fetch)


@pytest.fixture
def setup(client: TestClient) -> dict[str, Any]:
    """Un dossier avec une analyse (nom, adresses) et un modèle de quatre champs."""
    dossier_id, analysis = make_dossier(client)
    add_entity(client, analysis, "nom", "Dupont")
    add_entity(client, analysis, "adresse", "12 rue des Lilas", page=2)
    add_entity(client, analysis, "adresse", "3 place Neuve", page=1)
    template_id = make_template(
        client,
        [
            field("nom", entity("nom")),
            field("adresses", entity("adresse"), type="list"),
            field("decision"),
            field("dossier", meta("dossier_name")),
        ],
    )
    return {"dossier_id": dossier_id, "analysis": analysis, "template_id": template_id}


# --- Création ---


def test_a_draft_starts_with_values_from_the_analysis_and_the_dossier(client: TestClient, setup: dict) -> None:
    draft = create_draft(client, setup["dossier_id"], setup["template_id"])
    fields = by_name(draft)

    assert draft["status"] == "brouillon" and draft["template_version_number"] == 1
    nom = fields["nom"]["current"]
    assert (nom["value"], nom["status"], nom["origin"]) == ("Dupont", "proposé", "analysis")
    assert nom["sources"][0]["type"] == "analysis_element" and nom["version_number"] == 1
    # Un champ « liste » reprend toutes les occurrences, dans l'ordre des pages.
    assert fields["adresses"]["current"]["value"] == ["3 place Neuve", "12 rue des Lilas"]
    # Un champ à renseigner au fil de l'instruction n'a pas de valeur.
    assert fields["decision"]["current"]["status"] == "non_renseigné" and fields["decision"]["current"]["value"] is None
    # Une métadonnée du dossier est un fait : validée d'office.
    assert fields["dossier"]["current"]["status"] == "validé"
    assert fields["dossier"]["current"]["value"].startswith("Dossier ")


def test_a_single_valued_field_takes_the_first_occurrence_by_page(client: TestClient, setup: dict) -> None:
    template_id = make_template(client, [field("adresse", entity("adresse"))])
    draft = create_draft(client, setup["dossier_id"], template_id)
    assert by_name(draft)["adresse"]["current"]["value"] == "3 place Neuve"


def test_an_analysis_field_without_data_is_not_filled(client: TestClient, setup: dict) -> None:
    template_id = make_template(client, [field("siret", entity("siret"))])
    current = by_name(create_draft(client, setup["dossier_id"], template_id))["siret"]["current"]
    assert current["status"] == "non_renseigné" and current["value"] is None


def test_a_draft_is_tied_to_a_frozen_revision_of_the_analysis(client: TestClient, setup: dict) -> None:
    draft = create_draft(client, setup["dossier_id"], setup["template_id"])
    # L'analyse change ensuite : le brouillon garde les valeurs de sa révision.
    element = add_entity(client, setup["analysis"], "nom", "Durand")
    assert element
    run(
        client,
        lambda s: _retained_update(s, setup["analysis"], "Dupond"),
    )
    again = client.get(url(setup["dossier_id"], draft["id"])).json()
    assert by_name(again)["nom"]["current"]["value"] == "Dupont"
    assert again["revision_id"] == draft["revision_id"]


async def _retained_update(session: Any, analysis: DossierAnalysis, value: str) -> None:
    from sqlalchemy import select

    repository = DossierAnalysisRepository(session)
    element = (
        (
            await session.execute(
                select(AnalysisElement).where(
                    AnalysisElement.analysis_id == analysis.id, AnalysisElement.definition_name == "nom"
                )
            )
        )
        .scalars()
        .first()
    )
    await repository.add_version(
        element, value={"value": value}, origin=ElementVersionOrigin.INSTRUCTOR, author_id="someone"
    )


def test_a_given_revision_is_used(client: TestClient, setup: dict) -> None:
    revision = client.post(
        f"/api/dossiers/{setup['dossier_id']}/analyses-dossier/{setup['analysis'].id}/revisions", json={"label": "v1"}
    ).json()
    run(client, lambda s: _retained_update(s, setup["analysis"], "Dupond"))
    draft = create_draft(client, setup["dossier_id"], setup["template_id"], revision_id=revision["id"])
    assert draft["revision_id"] == revision["id"]
    assert by_name(draft)["nom"]["current"]["value"] == "Dupont"  # l'ancienne valeur, pas la corrigée


def test_a_revision_of_another_dossier_is_refused(client: TestClient, setup: dict) -> None:
    other_id, other_analysis = make_dossier(client)
    revision = client.post(
        f"/api/dossiers/{other_id}/analyses-dossier/{other_analysis.id}/revisions", json={"label": "autre"}
    ).json()
    response = client.post(
        f"/api/dossiers/{setup['dossier_id']}/document-drafts",
        json={"template_id": setup["template_id"], "revision_id": revision["id"]},
    )
    assert response.status_code == 404


def test_a_dossier_without_analysis_cannot_get_a_draft(client: TestClient) -> None:
    analyse_id = client.post("/api/analyses", json={"name": "Vide", "description": "t"}).json()["id"]
    dossier_id = client.post("/api/dossiers", json={"name": "Sans analyse", "analyse_id": analyse_id}).json()["id"]
    template_id = make_template(client, [field("decision")])
    response = client.post(f"/api/dossiers/{dossier_id}/document-drafts", json={"template_id": template_id})
    assert response.status_code == 409


def test_unknown_and_archived_templates_are_refused(client: TestClient, setup: dict) -> None:
    unknown = client.post(
        f"/api/dossiers/{setup['dossier_id']}/document-drafts", json={"template_id": str(uuid.uuid4())}
    )
    assert unknown.status_code == 404

    async def archive(session: Any) -> None:
        repository = DocumentTemplateRepository(session)
        await repository.set_archived(await repository.get(uuid.UUID(setup["template_id"])), True)

    run(client, archive)
    archived = client.post(
        f"/api/dossiers/{setup['dossier_id']}/document-drafts", json={"template_id": setup["template_id"]}
    )
    assert archived.status_code == 409


def test_list_and_get_drafts(client: TestClient, setup: dict) -> None:
    draft = create_draft(client, setup["dossier_id"], setup["template_id"])
    listed = client.get(f"/api/dossiers/{setup['dossier_id']}/document-drafts").json()
    assert [d["id"] for d in listed] == [draft["id"]] and listed[0]["template_version_number"] == 1
    assert client.get(url(setup["dossier_id"], str(uuid.uuid4()))).status_code == 404
    assert client.get(f"/api/dossiers/{uuid.uuid4()}/document-drafts").status_code == 404


# --- Saisie, validation, rejet ---


def test_an_instructor_value_is_validated_and_versioned(client: TestClient, setup: dict) -> None:
    draft = create_draft(client, setup["dossier_id"], setup["template_id"])
    path = url(setup["dossier_id"], draft["id"], "/fields/decision")

    first = client.put(path, json={"value": "  Accordée  ", "reason": "Dossier complet"})
    second = client.put(path, json={"value": "Refusée"})

    assert first.status_code == 200, first.text
    assert first.json()["value"] == "Accordée" and first.json()["status"] == "validé"
    assert first.json()["origin"] == "instructor" and first.json()["reason"] == "Dossier complet"
    versions = client.get(path + "/versions").json()
    assert [(v["version_number"], v["value"]) for v in versions] == [(1, None), (2, "Accordée"), (3, "Refusée")]
    assert second.json()["version_number"] == 3


@pytest.mark.parametrize(
    ("field_type", "bad"),
    [("number", "abc"), ("number", True), ("boolean", "peut-être"), ("list", []), ("list", "texte"), ("text", "  ")],
)
def test_a_value_of_the_wrong_type_is_refused(client: TestClient, setup: dict, field_type: str, bad: Any) -> None:
    template_id = make_template(client, [field("champ", type=field_type)])
    draft = create_draft(client, setup["dossier_id"], template_id)
    response = client.put(url(setup["dossier_id"], draft["id"], "/fields/champ"), json={"value": bad})
    assert response.status_code == 422


@pytest.mark.parametrize(
    ("field_type", "given", "stored"),
    [("number", "1 250,5", 1250.5), ("number", 3, 3), ("boolean", "Oui", True), ("list", [" a ", "b"], ["a", "b"])],
)
def test_values_are_typed(client: TestClient, setup: dict, field_type: str, given: Any, stored: Any) -> None:
    template_id = make_template(client, [field("champ", type=field_type)])
    draft = create_draft(client, setup["dossier_id"], template_id)
    response = client.put(url(setup["dossier_id"], draft["id"], "/fields/champ"), json={"value": given})
    assert response.status_code == 200 and response.json()["value"] == stored


def test_validating_a_proposal_keeps_its_value_and_sources(client: TestClient, setup: dict) -> None:
    draft = create_draft(client, setup["dossier_id"], setup["template_id"])
    proposed = by_name(draft)["nom"]["current"]
    response = client.post(url(setup["dossier_id"], draft["id"], "/fields/nom/validate"))
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "validé" and body["value"] == "Dupont" and body["origin"] == "analysis"
    assert body["sources"] == proposed["sources"] and body["version_number"] == 2 and body["author_id"]


def test_validating_something_that_is_not_proposed_is_refused(client: TestClient, setup: dict) -> None:
    draft = create_draft(client, setup["dossier_id"], setup["template_id"])
    for name in ("decision", "dossier"):  # non renseigné ; déjà validé
        response = client.post(url(setup["dossier_id"], draft["id"], f"/fields/{name}/validate"))
        assert response.status_code == 409


def test_rejecting_a_proposal_clears_the_field(client: TestClient, setup: dict) -> None:
    draft = create_draft(client, setup["dossier_id"], setup["template_id"])
    response = client.post(url(setup["dossier_id"], draft["id"], "/fields/nom/reject"), json={"reason": "Faux"})
    assert response.status_code == 200
    assert (response.json()["status"], response.json()["value"]) == ("non_renseigné", None)
    assert client.post(url(setup["dossier_id"], draft["id"], "/fields/nom/reject"), json={}).status_code == 409


def test_validate_all_proposals_at_once(client: TestClient, setup: dict) -> None:
    draft = create_draft(client, setup["dossier_id"], setup["template_id"])
    response = client.post(url(setup["dossier_id"], draft["id"], "/validate"), json={})
    assert response.status_code == 200 and sorted(v["field_name"] for v in response.json()) == ["adresses", "nom"]
    assert client.get(url(setup["dossier_id"], draft["id"], "/completeness")).json()["proposed"] == []


def test_validate_some_proposals_and_all_or_nothing(client: TestClient, setup: dict) -> None:
    draft = create_draft(client, setup["dossier_id"], setup["template_id"])
    path = url(setup["dossier_id"], draft["id"], "/validate")
    # « decision » n'est pas proposé : rien n'est validé, pas même « nom ».
    assert client.post(path, json={"names": ["nom", "decision"]}).status_code == 409
    assert by_name(client.get(url(setup["dossier_id"], draft["id"])).json())["nom"]["current"]["status"] == "proposé"
    assert client.post(path, json={"names": ["nom", "inconnu"]}).status_code == 404
    assert [v["field_name"] for v in client.post(path, json={"names": ["nom"]}).json()] == ["nom"]


def test_restoring_a_version_adds_a_version_with_its_value(client: TestClient, setup: dict) -> None:
    draft = create_draft(client, setup["dossier_id"], setup["template_id"])
    path = url(setup["dossier_id"], draft["id"], "/fields/decision")
    client.put(path, json={"value": "Accordée"})
    client.put(path, json={"value": "Refusée"})
    versions = client.get(path + "/versions").json()

    response = client.post(path + "/restore", json={"version_id": versions[1]["id"]})

    assert response.status_code == 200 and response.json()["value"] == "Accordée"
    assert response.json()["restored_from_version_id"] == versions[1]["id"] and response.json()["version_number"] == 4
    assert client.post(path + "/restore", json={"version_id": versions[0]["id"]}).status_code == 422  # version vide
    assert client.post(path + "/restore", json={"version_id": str(uuid.uuid4())}).status_code == 404


def test_an_unknown_field_is_404(client: TestClient, setup: dict) -> None:
    draft = create_draft(client, setup["dossier_id"], setup["template_id"])
    assert client.put(url(setup["dossier_id"], draft["id"], "/fields/inconnu"), json={"value": "x"}).status_code == 404
    assert client.get(url(setup["dossier_id"], draft["id"], "/fields/inconnu/versions")).status_code == 404


# --- Règle : une valeur validée n'est jamais réécrite automatiquement ---


def _propose(client: TestClient, setup: dict, draft: dict, name: str, value: Any, **extra: Any) -> Any:
    async def work(session: Any) -> Any:
        repository = DocumentDraftRepository(session)
        row = await repository.get(uuid.UUID(setup["dossier_id"]), uuid.UUID(draft["id"]))
        definition = next(d for d in template_definitions(await repository.template_version(row)) if d.name == name)
        return await repository.propose(
            row, definition, value, sources=[{"type": "page", "page": 3}], prompt_version="p1", model="m1", **extra
        )

    return run(client, work)


def test_the_agent_proposes_on_an_empty_field(client: TestClient, setup: dict) -> None:
    draft = create_draft(client, setup["dossier_id"], setup["template_id"])
    version = _propose(client, setup, draft, "decision", "Accordée")
    assert (version.status, version.origin, version.value) == ("proposé", "agent", "Accordée")
    assert (version.prompt_version, version.model) == ("p1", "m1")
    current = by_name(client.get(url(setup["dossier_id"], draft["id"])).json())["decision"]["current"]
    assert current["status"] == "proposé" and current["sources"] == [{"type": "page", "page": 3}]


def test_the_agent_never_rewrites_a_validated_value(client: TestClient, setup: dict) -> None:
    draft = create_draft(client, setup["dossier_id"], setup["template_id"])
    client.put(url(setup["dossier_id"], draft["id"], "/fields/decision"), json={"value": "Refusée"})

    with pytest.raises(ValidatedFieldError):
        _propose(client, setup, draft, "decision", "Accordée")
    with pytest.raises(ValidatedFieldError):  # y compris une valeur validée par accord avec la proposition
        client.post(url(setup["dossier_id"], draft["id"], "/fields/nom/validate"))
        _propose(client, setup, draft, "nom", "Autre")
    with pytest.raises(ValidatedFieldError):  # et une métadonnée du dossier
        _propose(client, setup, draft, "dossier", "Autre")

    current = by_name(client.get(url(setup["dossier_id"], draft["id"])).json())
    assert current["decision"]["current"]["value"] == "Refusée" and current["nom"]["current"]["value"] == "Dupont"
    assert len(client.get(url(setup["dossier_id"], draft["id"], "/fields/decision/versions")).json()) == 2


def test_a_proposal_can_be_regenerated_until_validated(client: TestClient, setup: dict) -> None:
    draft = create_draft(client, setup["dossier_id"], setup["template_id"])
    _propose(client, setup, draft, "decision", "Accordée")
    _propose(client, setup, draft, "decision", "Refusée", instruction="Plus court")
    events = client.get(url(setup["dossier_id"], draft["id"], "/events"), params={"field": "decision"}).json()
    assert [e["kind"] for e in events] == [FieldEventKind.PROPOSED, FieldEventKind.REGENERATED]
    assert events[1]["detail"] == "Plus court" and events[1]["prompt_version"] == "p1" and events[1]["model"] == "m1"


def test_an_agent_proposal_must_have_the_right_type(client: TestClient, setup: dict) -> None:
    from app.services.document_fields import FieldValueError

    draft = create_draft(client, setup["dossier_id"], setup["template_id"])
    with pytest.raises(FieldValueError):
        _propose(client, setup, draft, "adresses", "pas une liste")


# --- Champs renseignés au fil de l'instruction : recopie dans l'analyse ---


def test_a_validated_instruction_field_is_written_to_the_analysis(client: TestClient, setup: dict) -> None:
    draft = create_draft(client, setup["dossier_id"], setup["template_id"])
    assert element_fields(client, setup["analysis"], "decision") == []

    client.put(url(setup["dossier_id"], draft["id"], "/fields/decision"), json={"value": "Accordée"})

    (element,) = element_fields(client, setup["analysis"], "decision")
    analysis = client.get(f"/api/dossiers/{setup['dossier_id']}/analyses-dossier/{setup['analysis'].id}").json()
    written = next(e for e in analysis["elements"] if e["id"] == str(element.id))
    assert written["kind"] == "field" and written["retained_version"]["value"] == {"value": "Accordée"}
    assert written["retained_version"]["origin"] == "instructor"
    assert written["retained_version"]["source_type"] == "document_draft"
    assert written["retained_version"]["source_id"] == draft["id"]
    events = client.get(url(setup["dossier_id"], draft["id"], "/events"), params={"field": "decision"}).json()
    assert "Recopié dans l'analyse" in events[-1]["detail"]


def test_a_new_validated_value_adds_a_version_to_the_same_element(client: TestClient, setup: dict) -> None:
    draft = create_draft(client, setup["dossier_id"], setup["template_id"])
    path = url(setup["dossier_id"], draft["id"], "/fields/decision")
    client.put(path, json={"value": "Accordée"})
    client.put(path, json={"value": "Accordée"})  # inchangé : rien de plus dans l'analyse
    client.put(path, json={"value": "Refusée"})

    (element,) = element_fields(client, setup["analysis"], "decision")
    versions = client.get(
        f"/api/dossiers/{setup['dossier_id']}/analyses-dossier/{setup['analysis'].id}/elements/{element.id}/versions"
    ).json()
    assert [v["value"]["value"] for v in versions] == ["Accordée", "Refusée"]


def test_the_value_is_reused_by_another_document_of_the_same_dossier(client: TestClient, setup: dict) -> None:
    first = create_draft(client, setup["dossier_id"], setup["template_id"])
    client.put(url(setup["dossier_id"], first["id"], "/fields/decision"), json={"value": "Accordée"})

    other_template = make_template(client, [field("decision")])
    second = create_draft(client, setup["dossier_id"], other_template)

    current = by_name(second)["decision"]["current"]
    assert (current["value"], current["status"], current["origin"]) == ("Accordée", "proposé", "analysis")


def test_analysis_fields_are_not_copied_back(client: TestClient, setup: dict) -> None:
    draft = create_draft(client, setup["dossier_id"], setup["template_id"])
    client.put(url(setup["dossier_id"], draft["id"], "/fields/nom"), json={"value": "Dupond"})
    client.post(url(setup["dossier_id"], draft["id"], "/fields/adresses/validate"))
    assert element_fields(client, setup["analysis"], "nom") == []
    analysis = client.get(f"/api/dossiers/{setup['dossier_id']}/analyses-dossier/{setup['analysis'].id}").json()
    assert [e for e in analysis["elements"] if e["kind"] == "field"] == []


def test_a_frozen_analysis_is_not_written_to_but_the_draft_still_validates(client: TestClient, setup: dict) -> None:
    draft = create_draft(client, setup["dossier_id"], setup["template_id"])

    async def freeze(session: Any) -> None:
        row = await session.get(DossierAnalysis, setup["analysis"].id)
        row.status = DossierAnalysisStatus.FIGEE
        await session.commit()

    run(client, freeze)
    response = client.put(url(setup["dossier_id"], draft["id"], "/fields/decision"), json={"value": "Accordée"})
    assert response.status_code == 200 and response.json()["status"] == "validé"
    assert element_fields(client, setup["analysis"], "decision") == []
    events = client.get(url(setup["dossier_id"], draft["id"], "/events"), params={"field": "decision"}).json()
    assert "figée" in events[-1]["detail"]


def test_restoring_an_instruction_value_also_writes_it_to_the_analysis(client: TestClient, setup: dict) -> None:
    draft = create_draft(client, setup["dossier_id"], setup["template_id"])
    path = url(setup["dossier_id"], draft["id"], "/fields/decision")
    client.put(path, json={"value": "Accordée"})
    client.put(path, json={"value": "Refusée"})
    first = client.get(path + "/versions").json()[1]
    client.post(path + "/restore", json={"version_id": first["id"]})
    (element,) = element_fields(client, setup["analysis"], "decision")
    versions = client.get(
        f"/api/dossiers/{setup['dossier_id']}/analyses-dossier/{setup['analysis'].id}/elements/{element.id}/versions"
    ).json()
    assert [v["value"]["value"] for v in versions] == ["Accordée", "Refusée", "Accordée"]


# --- Complétude ---


def test_completeness_lists_required_fields_not_yet_validated(client: TestClient, setup: dict) -> None:
    template_id = make_template(
        client,
        [
            field("nom", entity("nom")),
            field("decision"),
            field("motif", required=False),
            field("genere", meta("generated_at")),
        ],
    )
    draft = create_draft(client, setup["dossier_id"], template_id)
    path = url(setup["dossier_id"], draft["id"], "/completeness")

    # « nom » proposé, « decision » vide ; « motif » facultatif et « genere » (posé à l'assemblage) ne comptent pas.
    assert client.get(path).json() == {"complete": False, "missing": ["decision"], "proposed": ["nom"]}
    assert draft["completeness"]["missing"] == ["decision"]

    client.post(url(setup["dossier_id"], draft["id"], "/fields/nom/validate"))
    client.put(url(setup["dossier_id"], draft["id"], "/fields/decision"), json={"value": "Accordée"})
    assert client.get(path).json() == {"complete": True, "missing": [], "proposed": []}


# --- Journal ---


def test_the_journal_records_every_decision_with_its_duration(client: TestClient, setup: dict) -> None:
    draft = create_draft(client, setup["dossier_id"], setup["template_id"])
    base = url(setup["dossier_id"], draft["id"])
    client.post(base + "/fields/nom/validate")  # accepté tel quel
    client.put(base + "/fields/adresses", json={"value": ["1 rue A"]})  # modifié
    client.post(base + "/fields/adresses/reject", json={})  # déjà validé : refusé, rien au journal
    client.put(base + "/fields/decision", json={"value": "Accordée"})  # saisie sans proposition

    events = client.get(base + "/events").json()
    kinds = [(e["field_name"], e["kind"]) for e in events]
    assert kinds == [
        ("nom", "proposed"),
        ("adresses", "proposed"),
        ("nom", "accepted"),
        ("adresses", "modified"),
        ("decision", "modified"),
    ]
    by_kind = {(e["field_name"], e["kind"]): e for e in events}
    assert by_kind[("nom", "accepted")]["duration_seconds"] >= 0  # tranche une proposition
    assert by_kind[("adresses", "modified")]["duration_seconds"] >= 0
    assert by_kind[("decision", "modified")]["duration_seconds"] is None  # rien n'était proposé
    assert by_kind[("nom", "accepted")]["author_id"] and by_kind[("nom", "proposed")]["author_id"] is None
    assert by_kind[("nom", "proposed")]["sources"][0]["type"] == "analysis_element"


def test_typing_the_proposed_value_counts_as_accepted(client: TestClient, setup: dict) -> None:
    draft = create_draft(client, setup["dossier_id"], setup["template_id"])
    client.put(url(setup["dossier_id"], draft["id"], "/fields/nom"), json={"value": "Dupont"})
    events = client.get(url(setup["dossier_id"], draft["id"], "/events"), params={"field": "nom"}).json()
    assert [e["kind"] for e in events] == ["proposed", "accepted"]


def test_the_journal_records_rejection_and_restoration(client: TestClient, setup: dict) -> None:
    draft = create_draft(client, setup["dossier_id"], setup["template_id"])
    base = url(setup["dossier_id"], draft["id"])
    client.post(base + "/fields/nom/reject", json={"reason": "Mauvaise pièce"})
    client.put(base + "/fields/nom", json={"value": "Durand"})
    first = client.get(base + "/fields/nom/versions").json()[1]  # la version « rejeté » est vide
    assert first["value"] is None
    versions = client.get(base + "/fields/nom/versions").json()
    client.put(base + "/fields/nom", json={"value": "Martin"})
    client.post(base + "/fields/nom/restore", json={"version_id": versions[2]["id"]})
    events = client.get(base + "/events", params={"field": "nom"}).json()
    assert [e["kind"] for e in events] == ["proposed", "rejected", "modified", "modified", "restored"]
    assert events[1]["detail"] == "Mauvaise pièce"


# --- Brouillon figé, archivé ---


def test_an_archived_draft_cannot_be_edited(client: TestClient, setup: dict) -> None:
    draft = create_draft(client, setup["dossier_id"], setup["template_id"])
    base = url(setup["dossier_id"], draft["id"])
    archived = client.post(base + "/archive")
    assert archived.status_code == 200 and archived.json()["status"] == "archivé"
    assert client.put(base + "/fields/decision", json={"value": "x"}).status_code == 409
    assert client.post(base + "/fields/nom/validate").status_code == 409
    assert client.post(base + "/validate", json={}).status_code == 409
    assert client.get(base).status_code == 200  # toujours consultable


# --- Concurrence ---


def test_two_writes_on_the_same_field_both_get_a_version(client: TestClient, setup: dict) -> None:
    draft = create_draft(client, setup["dossier_id"], setup["template_id"])
    path = url(setup["dossier_id"], draft["id"], "/fields/decision")
    for value in ("A", "B", "C"):
        assert client.put(path, json={"value": value}).status_code == 200
    numbers = [v["version_number"] for v in client.get(path + "/versions").json()]
    assert numbers == [1, 2, 3, 4]


def test_simultaneous_writes_on_a_field_never_collide(client: TestClient, setup: dict) -> None:
    """Deux instructeurs écrivent en même temps : chaque écriture obtient son numéro, aucune n'échoue."""
    import asyncio

    draft = create_draft(client, setup["dossier_id"], setup["template_id"])

    async def write(value: str) -> int:
        async with async_session_factory() as session:
            repository = DocumentDraftRepository(session)
            row = await repository.get(uuid.UUID(setup["dossier_id"]), uuid.UUID(draft["id"]))
            definition = next(
                d for d in template_definitions(await repository.template_version(row)) if d.name == "decision"
            )
            return (await repository.set_value(row, definition, value, user_id=value, reason=None)).version_number

    async def both() -> list[int]:
        return list(await asyncio.gather(*(write(f"valeur {i}") for i in range(6))))

    numbers = client.portal.call(both)
    assert sorted(numbers) == [2, 3, 4, 5, 6, 7]
    versions = client.get(url(setup["dossier_id"], draft["id"], "/fields/decision/versions")).json()
    assert [v["version_number"] for v in versions] == [1, 2, 3, 4, 5, 6, 7]


# --- Droits : interne, authentification requise ---


def test_the_routes_require_authentication(client: TestClient, setup: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi import HTTPException, status

    class NoAuth:
        def __call__(self, request: Any) -> None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    monkeypatch.setattr("app.core.security.factory.TokenVerifier", NoAuth())
    base = f"/api/dossiers/{setup['dossier_id']}/document-drafts"
    calls = [
        client.get(base),
        client.post(base, json={"template_id": setup["template_id"]}),
        client.get(f"{base}/{uuid.uuid4()}"),
        client.get(f"{base}/{uuid.uuid4()}/events"),
        client.put(f"{base}/{uuid.uuid4()}/fields/x", json={"value": "x"}),
    ]
    assert [c.status_code for c in calls] == [401] * len(calls)
