"""Tests de l'analyse de dossier (issue #112).

Le modèle est alimenté par la génération (#113), pas encore par les routes :
les tests créent leurs données via le repository, dans la boucle
d'évènements du TestClient (client.portal)."""

import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.db import async_session_factory
from app.models.dossier_analysis import (
    AnalysisElement,
    AnalysisElementKind,
    AnalysisUnitKind,
    AnalysisUnitStatus,
    DossierAnalysis,
    DossierAnalysisStatus,
    ElementVersionOrigin,
)
from app.repositories.dossier_analysis_repository import DossierAnalysisRepository
from app.schemas.dossier_analysis import InvalidElementValueError


def _create_dossier(client: TestClient, name: str = "Dossier analyse") -> str:
    analyse_id = client.post("/api/analyses", json={"name": "Analyse", "description": "Test"}).json()["id"]
    return client.post("/api/dossiers", json={"name": name, "analyse_id": analyse_id}).json()["id"]


def _run(client: TestClient, work: Callable[[DossierAnalysisRepository], Awaitable[Any]]) -> Any:
    async def runner() -> Any:
        async with async_session_factory() as session:
            return await work(DossierAnalysisRepository(session))

    return client.portal.call(runner)


def _new_analysis(client: TestClient, dossier_id: str, **kwargs: Any) -> DossierAnalysis:
    return _run(client, lambda repo: repo.create_analysis(uuid.UUID(dossier_id), **kwargs))


def _new_entity(client: TestClient, analysis: DossierAnalysis, value: str = "Dupont", **kwargs: Any) -> AnalysisElement:
    kwargs.setdefault("origin", ElementVersionOrigin.MODEL)
    return _run(
        client,
        lambda repo: repo.create_element(
            analysis, kind=AnalysisElementKind.ENTITY, value={"value": value}, definition_name="nom", **kwargs
        ),
    )


def _add_version(client: TestClient, element_id: uuid.UUID, **kwargs: Any) -> Any:
    async def work(repo: DossierAnalysisRepository) -> Any:
        element = await repo.db.get(AnalysisElement, element_id)
        return await repo.add_version(element, **kwargs)

    return _run(client, work)


def _url(dossier_id: str, analysis_id: Any = None, suffix: str = "") -> str:
    base = f"/api/dossiers/{dossier_id}"
    return f"{base}/analyses-dossier/{analysis_id}{suffix}" if analysis_id else f"{base}/analyse-dossier"


# --- Une analyse par exécution ---


def test_no_analysis_yet(client: TestClient) -> None:
    dossier_id = _create_dossier(client)
    assert client.get(_url(dossier_id)).status_code == 404
    assert client.get(f"/api/dossiers/{dossier_id}/analyses-dossier").json() == []


def test_unknown_dossier_is_404(client: TestClient) -> None:
    unknown = uuid.uuid4()
    assert client.get(f"/api/dossiers/{unknown}/analyse-dossier").status_code == 404
    assert client.get(f"/api/dossiers/{unknown}/analyses-dossier").status_code == 404


def test_current_analysis_is_the_most_recent(client: TestClient) -> None:
    dossier_id = _create_dossier(client)
    first = _new_analysis(client, dossier_id, analyse_version="v1", model="m1")
    second = _new_analysis(client, dossier_id, analyse_version="v2", previous_analysis_id=first.id)
    assert (first.sequence, second.sequence) == (1, 2)

    current = client.get(_url(dossier_id)).json()
    assert current["id"] == str(second.id)
    assert current["sequence"] == 2
    assert current["previous_analysis_id"] == str(first.id)
    assert current["status"] == "brouillon"

    listing = client.get(f"/api/dossiers/{dossier_id}/analyses-dossier").json()
    assert [a["sequence"] for a in listing] == [2, 1]
    # Une analyse précédente reste consultable.
    assert client.get(_url(dossier_id, first.id)).json()["analyse_version"] == "v1"


def test_analysis_of_another_dossier_is_404(client: TestClient) -> None:
    analysis = _new_analysis(client, _create_dossier(client, "A"))
    other = _create_dossier(client, "B")
    assert client.get(_url(other, analysis.id)).status_code == 404


# --- Éléments, versions, provenance ---


def test_model_element_keeps_prediction_and_pointers(client: TestClient) -> None:
    dossier_id = _create_dossier(client)
    analysis = _new_analysis(client, dossier_id)
    element = _new_entity(client, analysis, confidence=0.9)

    body = client.get(_url(dossier_id)).json()
    [out] = body["elements"]
    assert out["kind"] == "entity"
    assert out["definition_name"] == "nom"
    assert out["retained_version"]["value"] == {"value": "Dupont"}
    assert out["retained_version"]["origin"] == "model"
    assert out["retained_version"]["confidence"] == 0.9
    assert out["latest_model_version"]["id"] == out["retained_version"]["id"]
    assert out["needs_review"] is False
    assert out["id"] == str(element.id)


def test_instructor_version_does_not_overwrite_model_prediction(client: TestClient) -> None:
    dossier_id = _create_dossier(client)
    analysis = _new_analysis(client, dossier_id)
    element = _new_entity(client, analysis, "Dupond")
    _add_version(
        client,
        element.id,
        value={"value": "Dupont"},
        origin=ElementVersionOrigin.INSTRUCTOR,
        author_id="agent-1",
        reason="Faute de frappe sur la pièce",
        source_type="chat_message",
        source_id=uuid.uuid4(),
    )

    [out] = client.get(_url(dossier_id)).json()["elements"]
    assert out["retained_version"]["value"] == {"value": "Dupont"}
    assert out["retained_version"]["origin"] == "instructor"
    assert out["retained_version"]["author_id"] == "agent-1"
    assert out["retained_version"]["reason"] == "Faute de frappe sur la pièce"
    # La prédiction du modèle est conservée à côté.
    assert out["latest_model_version"]["value"] == {"value": "Dupond"}

    versions = client.get(_url(dossier_id, analysis.id, f"/elements/{element.id}/versions")).json()
    assert [v["version_number"] for v in versions] == [1, 2]
    assert [v["origin"] for v in versions] == ["model", "instructor"]


def test_new_model_version_does_not_replace_instructor_version(client: TestClient) -> None:
    dossier_id = _create_dossier(client)
    analysis = _new_analysis(client, dossier_id)
    element = _new_entity(client, analysis, "A")
    _add_version(client, element.id, value={"value": "B"}, origin=ElementVersionOrigin.INSTRUCTOR, author_id="u")
    _add_version(client, element.id, value={"value": "C"}, origin=ElementVersionOrigin.MODEL)

    [out] = client.get(_url(dossier_id)).json()["elements"]
    assert out["retained_version"]["value"] == {"value": "B"}
    assert out["latest_model_version"]["value"] == {"value": "C"}


def test_new_model_version_replaces_a_model_version(client: TestClient) -> None:
    dossier_id = _create_dossier(client)
    analysis = _new_analysis(client, dossier_id)
    element = _new_entity(client, analysis, "A")
    _add_version(client, element.id, value={"value": "B"}, origin=ElementVersionOrigin.MODEL)

    [out] = client.get(_url(dossier_id)).json()["elements"]
    assert out["retained_version"]["value"] == {"value": "B"}


def test_value_is_validated_per_kind(client: TestClient) -> None:
    analysis = _new_analysis(client, _create_dossier(client))
    with pytest.raises(InvalidElementValueError):
        _run(
            client,
            lambda repo: repo.create_element(
                analysis,
                kind=AnalysisElementKind.CLASSIFICATION,
                value={"value": "pas un label"},
                origin=ElementVersionOrigin.MODEL,
            ),
        )


def test_relation_links_existing_elements_of_the_same_analysis(client: TestClient) -> None:
    dossier_id = _create_dossier(client)
    analysis = _new_analysis(client, dossier_id)
    nom = _new_entity(client, analysis, "Dupont")
    adresse = _new_entity(client, analysis, "1 rue X")

    relation = _run(
        client,
        lambda repo: repo.create_element(
            analysis,
            kind=AnalysisElementKind.RELATION,
            value={"type": "habite_à", "source_element_id": str(nom.id), "target_element_id": str(adresse.id)},
            origin=ElementVersionOrigin.INSTRUCTOR,
            author_id="u",
        ),
    )
    assert relation.id is not None

    with pytest.raises(InvalidElementValueError):
        _run(
            client,
            lambda repo: repo.create_element(
                analysis,
                kind=AnalysisElementKind.RELATION,
                value={"type": "x", "source_element_id": str(nom.id), "target_element_id": str(uuid.uuid4())},
                origin=ElementVersionOrigin.INSTRUCTOR,
            ),
        )


def test_manual_element_has_no_unit_and_no_prediction(client: TestClient) -> None:
    dossier_id = _create_dossier(client)
    analysis = _new_analysis(client, dossier_id)
    _run(
        client,
        lambda repo: repo.create_element(
            analysis,
            kind=AnalysisElementKind.FIELD,
            value={"value": "oui"},
            origin=ElementVersionOrigin.INSTRUCTOR,
            author_id="u",
        ),
    )
    [out] = client.get(_url(dossier_id)).json()["elements"]
    assert out["unit_id"] is None
    assert out["source_prediction_id"] is None
    assert out["retained_version"]["origin"] == "instructor"
    assert out["latest_model_version"] is None


# --- Unités ---


def test_unit_without_element_is_recorded(client: TestClient) -> None:
    dossier_id = _create_dossier(client)
    analysis = _new_analysis(client, dossier_id)
    empty = _run(
        client,
        lambda repo: repo.create_unit(
            analysis.id,
            kind=AnalysisUnitKind.EXTRACTION,
            description={"pages": [1, 2]},
            input_fingerprint="a" * 64,
            status=AnalysisUnitStatus.TERMINE,
        ),
    )
    used = _run(client, lambda repo: repo.create_unit(analysis.id, kind=AnalysisUnitKind.CLASSIFICATION))
    _new_entity(client, analysis, unit=used)

    units = {u["id"]: u for u in client.get(_url(dossier_id, analysis.id, "/units")).json()}
    assert units[str(empty.id)]["element_count"] == 0
    assert units[str(empty.id)]["status"] == "terminé"
    assert units[str(empty.id)]["input_fingerprint"] == "a" * 64
    assert units[str(used.id)]["element_count"] == 1


# --- Restauration ---


def test_restore_adds_a_version_and_deletes_nothing(client: TestClient) -> None:
    dossier_id = _create_dossier(client)
    analysis = _new_analysis(client, dossier_id)
    element = _new_entity(client, analysis, "Dupond")
    _add_version(client, element.id, value={"value": "Dupont"}, origin=ElementVersionOrigin.INSTRUCTOR, author_id="u")
    versions = client.get(_url(dossier_id, analysis.id, f"/elements/{element.id}/versions")).json()
    first = versions[0]

    response = client.post(
        _url(dossier_id, analysis.id, f"/elements/{element.id}/restore"),
        json={"version_id": first["id"], "reason": "Finalement non"},
    )
    assert response.status_code == 201
    restored = response.json()
    assert restored["version_number"] == 3
    assert restored["value"] == {"value": "Dupond"}
    assert restored["restored_from_version_id"] == first["id"]
    assert restored["origin"] == "instructor"
    assert restored["reason"] == "Finalement non"

    [out] = client.get(_url(dossier_id)).json()["elements"]
    assert out["retained_version"]["id"] == restored["id"]
    after = client.get(_url(dossier_id, analysis.id, f"/elements/{element.id}/versions")).json()
    assert len(after) == 3
    # Les versions existantes n'ont pas bougé.
    assert after[:2] == versions


def test_restore_clears_the_review_flag(client: TestClient) -> None:
    dossier_id = _create_dossier(client)
    analysis = _new_analysis(client, dossier_id)
    element = _new_entity(client, analysis, "A")

    async def flag(repo: DossierAnalysisRepository) -> None:
        row = await repo.db.get(AnalysisElement, element.id)
        row.needs_review = True
        row.review_reason = "prompt modifié"
        await repo.db.commit()

    _run(client, flag)
    [out] = client.get(_url(dossier_id)).json()["elements"]
    assert out["needs_review"] is True
    assert out["review_reason"] == "prompt modifié"

    version_id = out["retained_version"]["id"]
    client.post(_url(dossier_id, analysis.id, f"/elements/{element.id}/restore"), json={"version_id": version_id})
    [out] = client.get(_url(dossier_id)).json()["elements"]
    assert out["needs_review"] is False
    assert out["review_reason"] is None


def test_restore_unknown_version_or_element_is_404(client: TestClient) -> None:
    dossier_id = _create_dossier(client)
    analysis = _new_analysis(client, dossier_id)
    element = _new_entity(client, analysis)
    other = _new_entity(client, analysis, "autre")
    other_version = client.get(_url(dossier_id, analysis.id, f"/elements/{other.id}/versions")).json()[0]

    unknown_version = client.post(
        _url(dossier_id, analysis.id, f"/elements/{element.id}/restore"), json={"version_id": str(uuid.uuid4())}
    )
    assert unknown_version.status_code == 404
    # Une version d'un autre élément ne peut pas être restaurée ici.
    foreign = client.post(
        _url(dossier_id, analysis.id, f"/elements/{element.id}/restore"), json={"version_id": other_version["id"]}
    )
    assert foreign.status_code == 404
    unknown_element = client.post(
        _url(dossier_id, analysis.id, f"/elements/{uuid.uuid4()}/restore"), json={"version_id": other_version["id"]}
    )
    assert unknown_element.status_code == 404


# --- Révisions ---


def test_revision_snapshots_retained_versions(client: TestClient) -> None:
    dossier_id = _create_dossier(client)
    analysis = _new_analysis(client, dossier_id)
    element = _new_entity(client, analysis, "Dupond")
    before = client.get(_url(dossier_id)).json()["elements"][0]["retained_version"]["id"]

    created = client.post(_url(dossier_id, analysis.id, "/revisions"), json={"label": "Avant correction"})
    assert created.status_code == 201
    revision = created.json()
    assert revision["number"] == 1
    assert revision["label"] == "Avant correction"
    assert revision["items"] == [{"element_id": str(element.id), "version_id": before}]

    # Une modification ultérieure ne change pas l'instantané.
    _add_version(client, element.id, value={"value": "Dupont"}, origin=ElementVersionOrigin.INSTRUCTOR, author_id="u")
    again = client.get(_url(dossier_id, analysis.id, f"/revisions/{revision['id']}")).json()
    assert again["items"] == revision["items"]

    second = client.post(_url(dossier_id, analysis.id, "/revisions"), json={}).json()
    assert second["number"] == 2
    assert second["items"][0]["version_id"] != before

    listing = client.get(_url(dossier_id, analysis.id, "/revisions")).json()
    assert [r["number"] for r in listing] == [2, 1]


def test_revision_of_unknown_analysis_or_revision_is_404(client: TestClient) -> None:
    dossier_id = _create_dossier(client)
    analysis = _new_analysis(client, dossier_id)
    assert client.post(_url(dossier_id, uuid.uuid4(), "/revisions"), json={}).status_code == 404
    assert client.get(_url(dossier_id, analysis.id, f"/revisions/{uuid.uuid4()}")).status_code == 404


# --- Idempotence (une prédiction ne produit qu'un élément) ---


def test_source_prediction_is_unique(client: TestClient) -> None:
    from sqlalchemy.exc import IntegrityError

    dossier_id = _create_dossier(client)
    analysis = _new_analysis(client, dossier_id)
    prediction_id = _create_prediction(client, dossier_id)
    _new_entity(client, analysis, source_prediction_id=prediction_id)
    with pytest.raises(IntegrityError):
        _new_entity(client, analysis, "autre", source_prediction_id=prediction_id)


def _create_prediction(client: TestClient, dossier_id: str) -> uuid.UUID:
    document = client.post(
        f"/api/dossiers/{dossier_id}/documents",
        files=[("files", ("cni.pdf", b"fake-bytes", "application/pdf"))],
    ).json()["documents"][0]
    page = client.post(
        f"/api/internal/documents/{document['id']}/pages",
        json={"page_number": 1, "content": "texte"},
        headers={"X-App-Token": "dev-only-worker-token-not-for-prod"},
    ).json()
    prediction = client.post(
        f"/api/internal/pages/{page['id']}/predictions",
        json={"kind": "entity", "name": "nom", "value": "Dupont", "confidence": 0.9},
        headers={"X-App-Token": "dev-only-worker-token-not-for-prod"},
    ).json()
    return uuid.UUID(prediction["id"])


# --- Création par un instructeur (routes) ---


def _elements_url(dossier_id: str, analysis_id: Any, suffix: str = "") -> str:
    return _url(dossier_id, analysis_id, f"/elements{suffix}")


def test_instructor_creates_an_element_by_hand(client: TestClient) -> None:
    dossier_id = _create_dossier(client)
    analysis = _new_analysis(client, dossier_id)

    response = client.post(
        _elements_url(dossier_id, analysis.id),
        json={
            "kind": "entity",
            "value": {"value": "12 rue des Lilas"},
            "definition_name": "adresse",
            "reason": "Relevé sur le justificatif papier",
            "source_type": "note",
        },
    )
    assert response.status_code == 201
    element = response.json()
    assert element["kind"] == "entity"
    assert element["definition_name"] == "adresse"
    assert element["unit_id"] is None
    assert element["latest_model_version"] is None
    version = element["retained_version"]
    assert version["origin"] == "instructor"
    assert version["author_id"]
    assert version["reason"] == "Relevé sur le justificatif papier"
    assert version["source_type"] == "note"

    # L'élément apparaît dans l'analyse courante.
    elements = client.get(_url(dossier_id)).json()["elements"]
    assert [e["id"] for e in elements] == [element["id"]]


def test_instructor_creates_a_relation_between_existing_elements(client: TestClient) -> None:
    dossier_id = _create_dossier(client)
    analysis = _new_analysis(client, dossier_id)
    nom = _new_entity(client, analysis, "Dupont")
    adresse = _new_entity(client, analysis, "1 rue X")

    response = client.post(
        _elements_url(dossier_id, analysis.id),
        json={
            "kind": "relation",
            "value": {"type": "habite_à", "source_element_id": str(nom.id), "target_element_id": str(adresse.id)},
        },
    )
    assert response.status_code == 201
    assert response.json()["retained_version"]["value"]["type"] == "habite_à"


def test_relation_to_unknown_element_is_422(client: TestClient) -> None:
    dossier_id = _create_dossier(client)
    analysis = _new_analysis(client, dossier_id)
    nom = _new_entity(client, analysis, "Dupont")
    response = client.post(
        _elements_url(dossier_id, analysis.id),
        json={
            "kind": "relation",
            "value": {"type": "x", "source_element_id": str(nom.id), "target_element_id": str(uuid.uuid4())},
        },
    )
    assert response.status_code == 422


def test_element_value_must_match_its_kind(client: TestClient) -> None:
    dossier_id = _create_dossier(client)
    analysis = _new_analysis(client, dossier_id)
    response = client.post(
        _elements_url(dossier_id, analysis.id), json={"kind": "classification", "value": {"value": "pas un label"}}
    )
    assert response.status_code == 422


def test_instructor_adds_a_version_with_author_and_reason(client: TestClient) -> None:
    dossier_id = _create_dossier(client)
    analysis = _new_analysis(client, dossier_id)
    element = _new_entity(client, analysis, "Dupond")
    message_id = str(uuid.uuid4())

    response = client.post(
        _elements_url(dossier_id, analysis.id, f"/{element.id}/versions"),
        json={
            "value": {"value": "Dupont"},
            "reason": "Corrigé après vérification téléphonique",
            "source_type": "chat_message",
            "source_id": message_id,
        },
    )
    assert response.status_code == 201
    version = response.json()
    assert version["version_number"] == 2
    assert version["origin"] == "instructor"
    assert version["author_id"]
    assert version["reason"] == "Corrigé après vérification téléphonique"
    assert version["source_type"] == "chat_message"
    assert version["source_id"] == message_id

    [out] = client.get(_url(dossier_id)).json()["elements"]
    assert out["retained_version"]["id"] == version["id"]
    # La prédiction du modèle reste accessible.
    assert out["latest_model_version"]["value"] == {"value": "Dupond"}


def test_version_requires_a_reason(client: TestClient) -> None:
    dossier_id = _create_dossier(client)
    analysis = _new_analysis(client, dossier_id)
    element = _new_entity(client, analysis)
    url = _elements_url(dossier_id, analysis.id, f"/{element.id}/versions")
    assert client.post(url, json={"value": {"value": "X"}}).status_code == 422
    assert client.post(url, json={"value": {"value": "X"}, "reason": ""}).status_code == 422


def test_version_value_must_match_the_element_kind(client: TestClient) -> None:
    dossier_id = _create_dossier(client)
    analysis = _new_analysis(client, dossier_id)
    element = _new_entity(client, analysis)
    response = client.post(
        _elements_url(dossier_id, analysis.id, f"/{element.id}/versions"),
        json={"value": {"label": "pas une entité"}, "reason": "test"},
    )
    assert response.status_code == 422


def test_add_version_to_unknown_element_is_404(client: TestClient) -> None:
    dossier_id = _create_dossier(client)
    analysis = _new_analysis(client, dossier_id)
    response = client.post(
        _elements_url(dossier_id, analysis.id, f"/{uuid.uuid4()}/versions"),
        json={"value": {"value": "X"}, "reason": "test"},
    )
    assert response.status_code == 404


def test_frozen_analysis_rejects_every_modification(client: TestClient) -> None:
    dossier_id = _create_dossier(client)
    analysis = _new_analysis(client, dossier_id)
    element = _new_entity(client, analysis, "A")
    version_id = client.get(_url(dossier_id)).json()["elements"][0]["retained_version"]["id"]

    async def freeze(repo: DossierAnalysisRepository) -> None:
        row = await repo.db.get(DossierAnalysis, analysis.id)
        row.status = DossierAnalysisStatus.FIGEE
        await repo.db.commit()

    _run(client, freeze)

    create = client.post(_elements_url(dossier_id, analysis.id), json={"kind": "entity", "value": {"value": "B"}})
    add = client.post(
        _elements_url(dossier_id, analysis.id, f"/{element.id}/versions"),
        json={"value": {"value": "B"}, "reason": "test"},
    )
    restore = client.post(
        _elements_url(dossier_id, analysis.id, f"/{element.id}/restore"), json={"version_id": version_id}
    )
    assert (create.status_code, add.status_code, restore.status_code) == (409, 409, 409)
    # La lecture reste possible, et rien n'a changé.
    assert len(client.get(_url(dossier_id)).json()["elements"]) == 1
    versions = client.get(_elements_url(dossier_id, analysis.id, f"/{element.id}/versions")).json()
    assert len(versions) == 1


def test_creation_in_analysis_of_another_dossier_is_404(client: TestClient) -> None:
    analysis = _new_analysis(client, _create_dossier(client, "A"))
    other = _create_dossier(client, "B")
    response = client.post(_elements_url(other, analysis.id), json={"kind": "entity", "value": {"value": "X"}})
    assert response.status_code == 404
