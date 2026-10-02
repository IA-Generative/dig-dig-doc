"""Tests de l'écran de revue d'un brouillon de document : aperçu, sources lisibles, valeurs sources modifiées (#142).

Le worker de rendu est simulé : il écrit dans le vrai S3 un « PDF » factice qui contient les valeurs reçues (JSON)."""

import json
import uuid
from datetime import timedelta
from typing import Any

import pytest
from document_helpers import add_entity, by_name, create_draft, entity, field, make_dossier, make_template, run, url
from fastapi.testclient import TestClient

from app.celery_client import RenderFailedError, RenderWorkerUnavailableError
from app.connectors import s3_connector
from app.models.dossier import DossierStatus
from app.models.dossier_analysis import AnalysisElement, ElementVersionOrigin
from app.repositories.dossier_analysis_repository import DossierAnalysisRepository
from app.repositories.dossier_repository import DossierRepository


@pytest.fixture(autouse=True)
def renderer(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    state: dict[str, Any] = {"calls": [], "error": None}

    def fake(template_key: str, values: dict, output_key: str, timeout: int = 120) -> str:
        state["calls"].append({"template_key": template_key, "values": values, "key": output_key})
        if state["error"]:
            raise state["error"]
        s3_connector.upload(output_key, b"%PDF-fake " + json.dumps(values).encode(), "application/pdf")
        return output_key

    monkeypatch.setattr("app.routers.document_drafts.render_preview", fake)
    return state


@pytest.fixture
def setup(client: TestClient) -> dict[str, Any]:
    dossier_id, analysis = make_dossier(client)
    add_entity(client, analysis, "nom", "Dupont", page=2)
    template_id = make_template(
        client,
        [
            field("nom", entity("nom")),
            field("decision"),
            field("motif", required=False),
            field("dossier", {"kind": "dossier_metadata", "key": "dossier_name"}),
            field("analyse", {"kind": "dossier_metadata", "key": "analysis_revision"}),
        ],
        dossier_id=dossier_id,
    )
    draft = create_draft(client, dossier_id, template_id)
    return {
        "dossier_id": dossier_id,
        "analysis": analysis,
        "draft": draft,
        "base": url(dossier_id, draft["id"]),
    }


def preview(client: TestClient, setup: dict[str, Any]):
    return client.get(setup["base"] + "/preview")


def pdf_values(response) -> dict[str, Any]:
    return json.loads(response.content[len(b"%PDF-fake ") :])


# --- Aperçu ---


def test_the_preview_is_the_pdf_of_the_template_filled_with_the_current_values(client: TestClient, setup: dict) -> None:
    response = preview(client, setup)

    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/pdf" and response.content.startswith(b"%PDF-")
    assert response.headers["content-disposition"].startswith("inline;")
    values = pdf_values(response)
    assert values["nom"] == "Dupont"  # seulement proposé : il entre dans l'aperçu (pas dans le document généré)
    assert values["decision"] == "[non renseigné]"  # obligatoire et vide : le trou se voit
    assert values["motif"] == ""  # facultatif et vide : rien
    assert values["dossier"].startswith("Dossier ") and values["analyse"] == str(setup["draft"]["revision_number"])


def test_the_preview_follows_the_values(client: TestClient, setup: dict, renderer) -> None:
    first = pdf_values(preview(client, setup))
    client.put(setup["base"] + "/fields/decision", json={"value": "Accordée"})

    second = preview(client, setup)

    assert pdf_values(second)["decision"] == "Accordée" and first["decision"] == "[non renseigné]"
    assert second.headers["x-preview-cache"] == "miss" and len(renderer["calls"]) == 2


def test_an_unchanged_preview_is_served_from_the_cache(client: TestClient, setup: dict, renderer) -> None:
    assert preview(client, setup).headers["x-preview-cache"] == "miss"
    # Valider la valeur proposée ne change pas ce que l'aperçu montre : même document, pas de nouveau rendu.
    client.post(setup["base"] + "/fields/nom/validate")
    again = preview(client, setup)

    assert again.headers["x-preview-cache"] == "hit" and len(renderer["calls"]) == 1
    assert pdf_values(again)["nom"] == "Dupont"


def test_the_preview_does_not_pile_up_in_s3(client: TestClient, setup: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.routers.document_drafts.PREVIEW_RETENTION", timedelta(0))
    preview(client, setup)
    client.put(setup["base"] + "/fields/decision", json={"value": "Accordée"})
    preview(client, setup)
    client.put(setup["base"] + "/fields/decision", json={"value": "Refusée"})
    last = preview(client, setup)

    prefix = f"previews/{setup['dossier_id']}/{setup['draft']['id']}/"
    objects = s3_connector.client.list_objects_v2(Bucket=s3_connector.bucket, Prefix=prefix).get("Contents", [])
    assert len(objects) == 1 and pdf_values(last)["decision"] == "Refusée"


def test_a_recent_preview_is_kept_so_a_concurrent_request_can_still_read_it(
    client: TestClient, setup: dict, renderer
) -> None:
    preview(client, setup)
    client.put(setup["base"] + "/fields/decision", json={"value": "Accordée"})
    preview(client, setup)
    keys = [call["key"] for call in renderer["calls"]]
    assert all(s3_connector.exists(k) for k in keys)  # moins de 10 minutes : rien n'est supprimé


def test_an_unavailable_worker_is_a_503_and_a_failure_a_502(client: TestClient, setup: dict, renderer) -> None:
    renderer["error"] = RenderWorkerUnavailableError()
    assert preview(client, setup).status_code == 503
    renderer["error"] = RenderFailedError("LibreOffice a échoué")
    failed = preview(client, setup)
    assert failed.status_code == 502 and "LibreOffice a échoué" in failed.json()["detail"]


def test_an_archived_draft_can_still_be_previewed(client: TestClient, setup: dict) -> None:
    client.post(setup["base"] + "/archive")
    assert preview(client, setup).status_code == 200


def test_the_preview_of_an_unknown_draft_is_404(client: TestClient, setup: dict) -> None:
    assert client.get(url(setup["dossier_id"], str(uuid.uuid4()), "/preview")).status_code == 404
    assert client.get(f"/api/dossiers/{uuid.uuid4()}/document-drafts/{setup['draft']['id']}/preview").status_code == 404


def test_deleting_the_dossier_deletes_its_previews(client: TestClient, setup: dict, renderer) -> None:
    preview(client, setup)
    key = renderer["calls"][0]["key"]
    assert s3_connector.exists(key)

    async def delete(session: Any) -> None:
        repository = DossierRepository(session)
        dossier = await repository.get(uuid.UUID(setup["dossier_id"]))
        dossier.status = DossierStatus.TERMINE
        await repository.delete_dossier(dossier)

    run(client, delete)
    assert not s3_connector.exists(key)


# --- Stockage : delete_prefix et exists ---


def test_delete_prefix_removes_only_matching_objects_and_can_spare_recent_ones() -> None:
    tag = uuid.uuid4().hex
    for name in ("a", "b"):
        s3_connector.upload(f"tests-prefix/{tag}/{name}", b"x", "text/plain")
    s3_connector.upload(f"tests-prefix/{tag}-autre/c", b"x", "text/plain")

    assert s3_connector.delete_prefix(f"tests-prefix/{tag}/", older_than=timedelta(hours=1)) == 0  # trop récents
    assert s3_connector.exists(f"tests-prefix/{tag}/a")
    assert s3_connector.delete_prefix(f"tests-prefix/{tag}/") == 2
    assert not s3_connector.exists(f"tests-prefix/{tag}/a") and s3_connector.exists(f"tests-prefix/{tag}-autre/c")
    s3_connector.delete(f"tests-prefix/{tag}-autre/c")


# --- Sources lisibles et valeurs sources modifiées ---


def test_the_sources_of_a_value_are_readable(client: TestClient, setup: dict) -> None:
    note = client.post(f"/api/dossiers/{setup['dossier_id']}/notes", json={"content": "Pièce vérifiée par téléphone"})
    draft = client.get(setup["base"]).json()
    fields = by_name(draft)

    (nom,) = fields["nom"]["source_details"]
    assert (nom["type"], nom["label"], nom["text"], nom["page"]) == ("analysis_element", "Entité « nom »", "Dupont", 2)
    assert fields["dossier"]["source_details"][0]["label"] == "Métadonnée du dossier"
    assert fields["decision"]["source_details"] == []  # rien d'où tirer : pas de source

    # Une valeur proposée par l'agent depuis une note : la note est lisible.
    run(client, lambda s: _propose_with_note(s, setup, note.json()["id"]))
    detail = by_name(client.get(setup["base"]).json())["decision"]["source_details"]
    assert detail[0]["label"] == "Note interne" and detail[0]["text"] == "Pièce vérifiée par téléphone"


async def _propose_with_note(session: Any, setup: dict, note_id: str) -> None:
    from app.repositories.document_draft_repository import DocumentDraftRepository, template_definitions

    repository = DocumentDraftRepository(session)
    draft = await repository.get(uuid.UUID(setup["dossier_id"]), uuid.UUID(setup["draft"]["id"]))
    definition = next(d for d in template_definitions(await repository.template_version(draft)) if d.name == "decision")
    await repository.propose(
        draft,
        definition,
        "Accordée",
        sources=[{"type": "note", "note_id": note_id, "version_number": 1}],
        prompt_version="p",
        model="m",
    )


def test_the_revision_number_is_shown(client: TestClient, setup: dict) -> None:
    draft = client.get(setup["base"]).json()
    assert draft["revision_number"] >= 1 and by_name(draft)["analyse"]["current"]["value"] == str(
        draft["revision_number"]
    )


def test_a_source_modified_since_the_revision_is_flagged(client: TestClient, setup: dict) -> None:
    assert [f["name"] for f in client.get(setup["base"]).json()["fields"] if f["stale"]] == []

    async def correct(session: Any) -> None:
        from sqlalchemy import select

        repository = DossierAnalysisRepository(session)
        element = (
            (
                await session.execute(
                    select(AnalysisElement).where(
                        AnalysisElement.analysis_id == setup["analysis"].id, AnalysisElement.definition_name == "nom"
                    )
                )
            )
            .scalars()
            .first()
        )
        await repository.add_version(
            element, value={"value": "Dupond"}, origin=ElementVersionOrigin.INSTRUCTOR, author_id="someone"
        )

    run(client, correct)
    fields = by_name(client.get(setup["base"]).json())
    assert fields["nom"]["stale"] is True  # sa source a été corrigée depuis
    assert fields["nom"]["current"]["value"] == "Dupont"  # le brouillon garde sa révision
    assert fields["decision"]["stale"] is False and fields["dossier"]["stale"] is False
