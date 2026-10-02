"""Tests des documents générés à partir d'un brouillon (issue #143).

Le worker de rendu est simulé : il écrit dans le vrai S3 un « ODT » qui contient les valeurs reçues (JSON) et un
« PDF » factice, ce qui permet de vérifier ce que le backend lui envoie, ce qu'il stocke et ce qu'il sert."""

import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Any

import pytest
from document_helpers import add_entity, create_draft, entity, field, make_dossier, make_template, run, url
from fastapi.testclient import TestClient

from app.celery_client import RenderFailedError, RenderWorkerUnavailableError
from app.connectors import s3_connector
from app.models.document_draft import DocumentDraft
from app.models.dossier import DossierStatus
from app.models.generated_document import GeneratedDocument
from app.repositories.dossier_repository import DossierRepository

ODT = "application/vnd.oasis.opendocument.text"


@pytest.fixture(autouse=True)
def renderer(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    state: dict[str, Any] = {"calls": [], "error": None}

    def fake(template_key: str, values: dict, prefix: str, timeout: int = 180) -> dict[str, str]:
        state["calls"].append({"template_key": template_key, "values": values, "prefix": prefix})
        if isinstance(state["error"], RenderWorkerUnavailableError):
            raise state["error"]
        s3_connector.upload(f"{prefix}.odt", json.dumps(values).encode(), ODT)
        if state["error"]:
            raise state["error"]  # échec après un dépôt partiel
        s3_connector.upload(f"{prefix}.pdf", b"%PDF-fake " + json.dumps(values).encode(), "application/pdf")
        return {"odt_key": f"{prefix}.odt", "pdf_key": f"{prefix}.pdf"}

    monkeypatch.setattr("app.routers.generated_documents.render_document", fake)
    return state


@pytest.fixture
def setup(client: TestClient) -> dict[str, Any]:
    dossier_id, analysis = make_dossier(client)
    add_entity(client, analysis, "nom", "Dupont")
    add_entity(client, analysis, "adresse", "3 place Neuve", page=1)
    add_entity(client, analysis, "adresse", "12 rue des Lilas", page=2)
    template_id = make_template(
        client,
        [
            field("nom", entity("nom")),
            field("adresses", entity("adresse"), type="list"),
            field("decision"),
            field("montant", type="number"),
            field("urgent", type="boolean", required=False),
            field("commentaire", required=False),
            field("dossier", {"kind": "dossier_metadata", "key": "dossier_name"}),
            field("date", {"kind": "dossier_metadata", "key": "generated_at"}, type="date"),
            field("analyse", {"kind": "dossier_metadata", "key": "analysis_revision"}),
            field("version", {"kind": "dossier_metadata", "key": "document_version"}),
        ],
        name="Décision d'octroi",
    )
    draft = create_draft(client, dossier_id, template_id)
    return {
        "dossier_id": dossier_id,
        "analysis": analysis,
        "draft": draft,
        "base": url(dossier_id, draft["id"]),
        "docs": f"/api/dossiers/{dossier_id}/generated-documents",
    }


def validate_all(client: TestClient, setup: dict[str, Any]) -> None:
    base = setup["base"]
    client.post(base + "/validate", json={})
    client.put(base + "/fields/decision", json={"value": "Accordée"})
    client.put(base + "/fields/montant", json={"value": "1 250,5"})
    client.put(base + "/fields/urgent", json={"value": "oui"})


def generate(client: TestClient, setup: dict[str, Any], **body: Any):
    return client.post(setup["base"] + "/documents", json=body)


def stored(key: str) -> bytes:
    return s3_connector.download(key)[0]


# --- Assemblage ---


def test_the_document_is_assembled_from_the_validated_values(client: TestClient, setup: dict, renderer) -> None:
    validate_all(client, setup)

    response = generate(client, setup)

    assert response.status_code == 201, response.text
    body = response.json()
    values = body["values"]
    assert values["nom"] == "Dupont" and values["adresses"] == ["3 place Neuve", "12 rue des Lilas"]
    assert values["decision"] == "Accordée" and values["urgent"] == "oui"
    assert values["montant"] == "1250,5"  # nombre écrit à la française
    assert values["dossier"].startswith("Dossier ")
    assert values["commentaire"] == ""  # facultatif, jamais renseigné : vide, pas de trou
    today = datetime.now(UTC).date()
    assert values["date"] == today.strftime("%d/%m/%Y")  # date écrite JJ/MM/AAAA
    assert values["analyse"] == str(body["revision_number"]) and values["version"] == "1"
    assert body["version_number"] == 1 and body["incomplete_fields"] == []
    assert body["visibility"] == "interne" and body["has_pdf"] is True
    assert body["template_name"].startswith("Décision d'octroi") and body["template_version_number"] == 1
    assert body["odt_size"] and body["pdf_size"] and body["author_id"]
    # Le worker a reçu les valeurs et le modèle de la version utilisée par le brouillon.
    (call,) = renderer["calls"]
    assert call["values"] == values and call["template_key"].startswith("document-templates/")
    assert call["prefix"] == f"generated-documents/{setup['dossier_id']}/{setup['draft']['id']}/v1"


def test_only_validated_values_enter_the_document(client: TestClient, setup: dict) -> None:
    validate_all(client, setup)
    # Un champ facultatif simplement proposé n'entre pas : on n'écrit que ce qui est validé.
    template_id = make_template(client, [field("nom", entity("nom")), field("note", required=False)])
    draft = create_draft(client, setup["dossier_id"], template_id)
    run(client, lambda s: _propose(s, setup["dossier_id"], draft["id"], "note", "Proposée par l'agent"))
    client.post(url(setup["dossier_id"], draft["id"], "/fields/nom/validate"))
    response = client.post(url(setup["dossier_id"], draft["id"], "/documents"), json={})
    assert response.status_code == 201
    assert response.json()["values"] == {"nom": "Dupont", "note": ""}


async def _propose(session: Any, dossier_id: str, draft_id: str, name: str, value: str) -> None:
    from app.repositories.document_draft_repository import DocumentDraftRepository, template_definitions

    repository = DocumentDraftRepository(session)
    draft = await repository.get(uuid.UUID(dossier_id), uuid.UUID(draft_id))
    definition = next(d for d in template_definitions(await repository.template_version(draft)) if d.name == name)
    await repository.propose(draft, definition, value, sources=[], prompt_version="p", model="m")


def test_a_proposed_required_field_refuses_the_generation(client: TestClient, setup: dict, renderer) -> None:
    # « nom » et « adresses » sont seulement proposés ; « decision » et « montant » vides.
    response = generate(client, setup)
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["incomplete_fields"] == ["nom", "adresses", "decision", "montant"]
    assert "confirmez" in detail["message"]
    assert renderer["calls"] == [] and client.get(setup["docs"]).json() == []  # rien n'est lancé ni stocké


def test_an_incomplete_document_needs_an_explicit_confirmation_and_says_so(client: TestClient, setup: dict) -> None:
    client.put(setup["base"] + "/fields/decision", json={"value": "Accordée"})

    response = generate(client, setup, confirm_incomplete=True)

    assert response.status_code == 201
    body = response.json()
    assert body["incomplete_fields"] == ["nom", "adresses", "montant"]
    assert body["values"]["nom"] == "[non renseigné]" and body["values"]["adresses"] == ["[non renseigné]"]
    assert body["values"]["decision"] == "Accordée"


def test_regenerating_adds_a_version_and_keeps_the_old_one_frozen(client: TestClient, setup: dict) -> None:
    validate_all(client, setup)
    first = generate(client, setup).json()
    client.put(setup["base"] + "/fields/decision", json={"value": "Refusée"})
    second = generate(client, setup).json()

    assert (first["version_number"], second["version_number"]) == (1, 2)
    assert second["values"]["decision"] == "Refusée" and second["values"]["version"] == "2"
    # L'ancienne version n'a pas bougé : valeurs et fichier.
    assert client.get(f"{setup['docs']}/{first['id']}").json()["values"]["decision"] == "Accordée"
    old = client.get(f"{setup['docs']}/{first['id']}/file")
    assert json.loads(old.content)["decision"] == "Accordée"
    assert json.loads(client.get(f"{setup['docs']}/{second['id']}/file").content)["decision"] == "Refusée"
    assert [d["version_number"] for d in client.get(setup["docs"]).json()] == [2, 1]  # le plus récent d'abord


def test_the_source_revision_of_the_analysis_is_traced(client: TestClient, setup: dict) -> None:
    validate_all(client, setup)
    document = generate(client, setup).json()
    assert document["revision_id"] == setup["draft"]["revision_id"]
    assert document["analysis_id"] == setup["draft"]["analysis_id"]
    # Une nouvelle révision de l'analyse n'y change rien : le brouillon reste lié à la sienne.
    client.post(
        f"/api/dossiers/{setup['dossier_id']}/analyses-dossier/{setup['analysis'].id}/revisions",
        json={"label": "après"},
    )
    again = generate(client, setup).json()
    assert again["revision_number"] == document["revision_number"]


def test_special_characters_and_long_lists_are_passed_as_they_are(client: TestClient, setup: dict) -> None:
    validate_all(client, setup)
    client.put(setup["base"] + "/fields/decision", json={"value": 'Accordée & "validée" <sous réserve> 5 € — ’'})
    client.put(setup["base"] + "/fields/adresses", json={"value": [f"{i} rue de l'Exemple" for i in range(60)]})
    body = generate(client, setup).json()
    assert body["values"]["decision"] == 'Accordée & "validée" <sous réserve> 5 € — ’'
    assert len(body["values"]["adresses"]) == 60


def test_a_list_field_with_one_item_stays_a_list(client: TestClient, setup: dict) -> None:
    validate_all(client, setup)
    client.put(setup["base"] + "/fields/adresses", json={"value": ["Seule adresse"]})
    assert generate(client, setup).json()["values"]["adresses"] == ["Seule adresse"]


# --- Téléchargement ---


def test_the_odt_and_the_pdf_can_be_downloaded(client: TestClient, setup: dict) -> None:
    validate_all(client, setup)
    document = generate(client, setup).json()
    path = f"{setup['docs']}/{document['id']}/file"

    odt = client.get(path)
    assert odt.status_code == 200 and odt.headers["content-type"] == ODT
    assert odt.headers["content-disposition"].startswith("attachment;")
    assert "filename*=UTF-8''D%C3%A9cision-d-octroi" in odt.headers["content-disposition"]  # nom accentué conservé
    assert document["file_name"].startswith("Décision-d-octroi") and odt.headers["cache-control"] == "private, no-store"
    assert json.loads(odt.content)["nom"] == "Dupont"

    pdf = client.get(path, params={"format": "pdf"})
    assert pdf.status_code == 200 and pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF-") and ".pdf" in pdf.headers["content-disposition"]
    preview = client.get(path, params={"format": "pdf", "inline": True})
    assert preview.headers["content-disposition"].startswith("inline;")
    # L'ODT se télécharge toujours : jamais affiché dans le navigateur.
    assert client.get(path, params={"inline": True}).headers["content-disposition"].startswith("attachment;")
    assert client.get(path, params={"format": "docx"}).status_code == 422


def test_a_document_without_pdf_has_no_pdf_to_download(client: TestClient, setup: dict) -> None:
    validate_all(client, setup)
    document = generate(client, setup).json()

    async def drop(session: Any) -> None:
        row = await session.get(GeneratedDocument, uuid.UUID(document["id"]))
        row.pdf_key = None
        await session.commit()

    run(client, drop)
    assert client.get(f"{setup['docs']}/{document['id']}").json()["has_pdf"] is False
    assert client.get(f"{setup['docs']}/{document['id']}/file", params={"format": "pdf"}).status_code == 404


def test_unknown_or_foreign_documents_are_404(client: TestClient, setup: dict) -> None:
    validate_all(client, setup)
    document = generate(client, setup).json()
    other_dossier, _ = make_dossier(client)
    assert client.get(f"{setup['docs']}/{uuid.uuid4()}").status_code == 404
    assert client.get(f"/api/dossiers/{other_dossier}/generated-documents/{document['id']}").status_code == 404
    assert client.get(f"/api/dossiers/{other_dossier}/generated-documents/{document['id']}/file").status_code == 404
    assert client.get(f"/api/dossiers/{uuid.uuid4()}/generated-documents").status_code == 404


def test_the_list_can_be_filtered_by_draft(client: TestClient, setup: dict) -> None:
    validate_all(client, setup)
    generate(client, setup)
    other_template = make_template(client, [field("nom", entity("nom"))])
    other = create_draft(client, setup["dossier_id"], other_template)
    client.post(url(setup["dossier_id"], other["id"], "/fields/nom/validate"))
    client.post(url(setup["dossier_id"], other["id"], "/documents"), json={})

    assert len(client.get(setup["docs"]).json()) == 2
    only = client.get(setup["docs"], params={"draft_id": setup["draft"]["id"]}).json()
    assert [d["draft_id"] for d in only] == [setup["draft"]["id"]]


# --- Refus et pannes ---


def test_an_archived_draft_or_running_generation_blocks_the_assembly(client: TestClient, setup: dict) -> None:
    validate_all(client, setup)

    async def start(session: Any) -> None:
        row = await session.get(DocumentDraft, uuid.UUID(setup["draft"]["id"]))
        row.generation_status, row.generation_requested_at = "en_cours", datetime.now(UTC)
        await session.commit()

    run(client, start)
    running = generate(client, setup)
    assert running.status_code == 409 and "en cours de génération" in running.json()["detail"]

    client.post(setup["base"] + "/archive")
    assert generate(client, setup).status_code == 409


def test_an_unavailable_worker_stores_nothing(client: TestClient, setup: dict, renderer) -> None:
    validate_all(client, setup)
    renderer["error"] = RenderWorkerUnavailableError()
    assert generate(client, setup).status_code == 503
    assert client.get(setup["docs"]).json() == []
    renderer["error"] = None
    assert generate(client, setup).json()["version_number"] == 1  # le numéro n'est pas consommé


def test_a_failed_rendering_leaves_no_partial_file(client: TestClient, setup: dict, renderer) -> None:
    validate_all(client, setup)
    renderer["error"] = RenderFailedError("LibreOffice a échoué")

    response = generate(client, setup)

    assert response.status_code == 502 and "LibreOffice a échoué" in response.json()["detail"]
    assert client.get(setup["docs"]).json() == []
    prefix = renderer["calls"][0]["prefix"]
    with pytest.raises(Exception):  # noqa: B017, PT011 - l'ODT déposé avant l'échec a été retiré
        s3_connector.download(f"{prefix}.odt")


def test_simultaneous_generations_get_distinct_versions(client: TestClient, setup: dict) -> None:
    validate_all(client, setup)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: generate(client, setup), range(4)))
    assert [r.status_code for r in results] == [201] * 4
    assert sorted(r.json()["version_number"] for r in results) == [1, 2, 3, 4]


# --- Suppression du dossier ---


def test_deleting_the_dossier_deletes_its_generated_files(client: TestClient, setup: dict) -> None:
    validate_all(client, setup)
    document = generate(client, setup).json()
    keys = [
        f"generated-documents/{setup['dossier_id']}/{setup['draft']['id']}/v1.odt",
        f"generated-documents/{setup['dossier_id']}/{setup['draft']['id']}/v1.pdf",
    ]
    assert all(stored(k) for k in keys)

    async def delete(session: Any) -> None:
        repository = DossierRepository(session)
        dossier = await repository.get(uuid.UUID(setup["dossier_id"]))
        dossier.status = DossierStatus.TERMINE  # un dossier actif se supprime après avoir été arrêté
        await repository.delete_dossier(dossier)

    run(client, delete)

    for key in keys:
        with pytest.raises(Exception):  # noqa: B017, PT011
            s3_connector.download(key)

    async def rows(session: Any) -> Any:
        return await session.get(GeneratedDocument, uuid.UUID(document["id"]))

    assert run(client, rows) is None  # la ligne est partie par cascade


# --- Droits : interne, authentification requise ---


def test_the_routes_require_authentication(client: TestClient, setup: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi import HTTPException, status

    class NoAuth:
        def __call__(self, request: Any) -> None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    validate_all(client, setup)
    document = generate(client, setup).json()
    monkeypatch.setattr("app.core.security.factory.TokenVerifier", NoAuth())
    calls = [
        client.post(setup["base"] + "/documents", json={}),
        client.get(setup["docs"]),
        client.get(f"{setup['docs']}/{document['id']}"),
        client.get(f"{setup['docs']}/{document['id']}/file"),
    ]
    assert [c.status_code for c in calls] == [401] * 4


# --- Valeurs de métadonnées posées à la création du brouillon ---


def test_the_analysis_revision_is_written_at_draft_creation_and_assembly_values_are_not(
    client: TestClient, setup: dict
) -> None:
    fields = {f["name"]: f["current"] for f in setup["draft"]["fields"]}
    assert fields["analyse"]["status"] == "validé" and fields["analyse"]["value"].isdigit()
    # generated_at et document_version sont posées à l'assemblage : vides ici, sans bloquer la complétude.
    assert fields["date"]["value"] is None and fields["version"]["value"] is None
    assert "date" not in setup["draft"]["completeness"]["missing"]
    assert "version" not in setup["draft"]["completeness"]["missing"]
