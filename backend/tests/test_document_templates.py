"""Tests des modèles de document et de leurs champs (issue #138)."""

import io
import json
import uuid
import zipfile
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.celery_client import RenderWorkerUnavailableError, TemplateExtractionError
from app.core.security.factory import RequestContext, get_current_user
from app.main import app

ODT_MIME = "application/vnd.oasis.opendocument.text"
URL = "/api/admin/document-templates"
# La base garde les modèles des exécutions précédentes et un nom est unique : chaque exécution a ses noms.
RUN = uuid.uuid4().hex[:8]


def n(name: str) -> str:
    return f"{name.rstrip()} {RUN}"


def make_odt(*placeholders: str) -> bytes:
    """Un ODT minimal : le backend ne lit que l'archive et son type ; les placeholders sont lus par le worker
    (simulé dans ces tests par la liste transmise)."""
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        archive.writestr(zipfile.ZipInfo("mimetype"), ODT_MIME, zipfile.ZIP_STORED)
        archive.writestr(
            "content.xml", "<office:document-content>" + " ".join(placeholders) + "</office:document-content>"
        )
    return out.getvalue()


# L'analyse du test en cours : un modèle appartient à une analyse (issue #139).
CURRENT: dict[str, str] = {}


def make_analyse(
    client: TestClient, *, entities=("nom", "adresse"), labels=("Passeport",), agents=("Synthèse",)
) -> str:
    """Une analyse qui définit des entités, des labels et des agents (les éléments que les champs peuvent viser)."""
    analyse_id = client.post("/api/analyses", json={"name": f"Analyse {RUN}", "description": "t"}).json()["id"]
    client.put(
        f"/api/analyses/{analyse_id}/extraction/entities",
        json={"entities": [{"name": e, "definition": f"def {e}", "type": "texte"} for e in entities]},
    )
    client.put(
        f"/api/analyses/{analyse_id}/classification/labels",
        json={"labels": [{"name": label, "definition": f"def {label}"} for label in labels]},
    )
    for agent in agents:
        client.post(f"/api/analyses/{analyse_id}/agents", json={"name": agent, "prompt": "p", "tools": []})
    return analyse_id


@pytest.fixture(autouse=True)
def analyse(client: TestClient) -> str:
    CURRENT["analyse_id"] = make_analyse(client)
    return CURRENT["analyse_id"]


@pytest.fixture(autouse=True)
def worker(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Remplace le worker de rendu : il « lit » les placeholders écrits entre {{ }} dans le fichier."""
    state: dict[str, Any] = {"calls": 0, "error": None}

    def fake_extract(key: str, timeout: int = 30) -> list[str]:
        from app.connectors import s3_connector

        state["calls"] += 1
        if state["error"]:
            raise state["error"]
        data, _ = s3_connector.download(key)
        content = zipfile.ZipFile(io.BytesIO(data)).read("content.xml").decode()
        return sorted({p.strip() for p in content.replace("{{", "\0").replace("}}", "\0").split("\0")[1::2]})

    monkeypatch.setattr("app.routers.admin_document_templates.extract_template_fields", fake_extract)
    return state


NOT_ODT = {"file": ("m.odt", b"texte", ODT_MIME)}


def base() -> dict[str, str]:
    """Champs de formulaire communs aux créations : l'analyse du test en cours et un nom."""
    return {"analyse_id": CURRENT["analyse_id"], "name": "X"}


def field(name: str, **extra: Any) -> dict[str, Any]:
    return {"name": name, "label": name.capitalize(), "source": {"kind": "instruction"}, **extra}


def odt(*names: str) -> bytes:
    return make_odt(*(f"{{{{ {x} }}}}" for x in names))


def create(
    client: TestClient, name: str, names: tuple[str, ...] = ("nom",), fields: list[dict] | None = None, **form: str
):
    return client.post(
        URL,
        data={
            "analyse_id": CURRENT["analyse_id"],
            "name": n(name),
            "fields": json.dumps(fields if fields is not None else [field(x) for x in names]),
            **form,
        },
        files={"file": ("modele.odt", odt(*names), ODT_MIME)},
    )


def new_version(client: TestClient, template_id: str, name: str, fields: list[dict], file: bytes | None = None, **form):
    files = {"file": ("v.odt", file, ODT_MIME)} if file is not None else None
    return client.post(
        f"{URL}/{template_id}/versions", data={"name": n(name), "fields": json.dumps(fields), **form}, files=files
    )


# --- Créer et lire ---


def test_create_a_template_with_its_fields(client: TestClient, worker: dict) -> None:
    fields = [
        field("nom", label="Nom du demandeur", type="text", instruction="En majuscules"),
        {
            "name": "date_decision",
            "label": "Date",
            "type": "date",
            "required": False,
            "source": {"kind": "dossier_metadata", "key": "dossier_ended_at"},
        },
        {
            "name": "adresse",
            "label": "Adresse",
            "source": {"kind": "analysis", "element_kind": "entity", "definition_name": "adresse"},
        },
    ]
    response = create(client, "Décision A", ("nom", "date_decision", "adresse"), fields, description="  Courrier  ")

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == n("Décision A") and body["description"] == "Courrier"
    assert body["version_number"] == 1 and body["archived"] is False
    assert body["placeholders"] == ["adresse", "date_decision", "nom"]
    assert body["fields"][0]["instruction"] == "En majuscules" and body["fields"][1]["required"] is False
    assert body["fields"][2]["source"]["selection"] == "retained_or_predicted"
    assert body["file_name"] == "modele.odt" and body["file_size"] > 0
    assert client.get(f"{URL}/{body['id']}").json()["id"] == body["id"]
    assert body["id"] in [t["id"] for t in client.get(URL).json()]


def test_the_file_is_stored_and_downloadable(client: TestClient) -> None:
    template = create(client, "Décision B").json()
    response = client.get(f"{URL}/{template['id']}/versions/1/file")
    assert response.status_code == 200 and response.headers["content-type"] == ODT_MIME
    assert 'filename="modele.odt"' in response.headers["content-disposition"]
    assert zipfile.ZipFile(io.BytesIO(response.content)).read("mimetype") == ODT_MIME.encode()
    assert client.get(f"{URL}/{template['id']}/versions/9/file").status_code == 404


def test_an_unknown_template_is_404(client: TestClient) -> None:
    assert client.get(f"{URL}/00000000-0000-0000-0000-000000000000").status_code == 404


# --- Validation à l'import, dans les deux sens ---


def test_an_unknown_placeholder_is_refused_with_a_readable_report(client: TestClient) -> None:
    response = create(client, "Décision C", ("nom", "adresse"), [field("nom")])
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["unknown_placeholders"] == ["adresse"] and detail["unused_fields"] == []
    assert "ne correspondent pas" in detail["message"]


def test_a_field_missing_from_the_file_is_refused(client: TestClient) -> None:
    response = create(client, "Décision D", ("nom",), [field("nom"), field("motif")])
    assert response.status_code == 422
    assert response.json()["detail"]["unused_fields"] == ["motif"]


def test_nothing_is_saved_when_the_import_is_refused(client: TestClient) -> None:
    before = len(client.get(URL, params={"include_archived": True}).json())
    create(client, "Jamais créé", ("nom", "x"), [field("nom")])
    assert len(client.get(URL, params={"include_archived": True}).json()) == before


def test_inspect_lists_placeholders_without_saving(client: TestClient) -> None:
    before = len(client.get(URL, params={"include_archived": True}).json())
    response = client.post(f"{URL}/inspect", files={"file": ("m.odt", odt("b", "a"), ODT_MIME)})
    assert response.status_code == 200
    assert response.json() == {"placeholders": ["a", "b"], "file_name": "m.odt", "file_size": len(odt("b", "a"))}
    assert len(client.get(URL, params={"include_archived": True}).json()) == before


def test_a_file_that_is_not_an_odt_is_refused(client: TestClient, worker: dict) -> None:
    response = client.post(
        URL,
        data={"analyse_id": CURRENT["analyse_id"], "name": "X", "fields": "[]"},
        files={"file": ("m.odt", b"texte", ODT_MIME)},
    )
    assert response.status_code == 422 and "ODT" in response.json()["detail"]
    assert worker["calls"] == 0  # le worker n'est même pas sollicité


def test_a_zip_of_another_type_is_refused(client: TestClient) -> None:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        archive.writestr("mimetype", "application/vnd.oasis.opendocument.spreadsheet")
    response = client.post(f"{URL}/inspect", files={"file": ("m.ods", out.getvalue(), ODT_MIME)})
    assert response.status_code == 422 and "ODT" in response.json()["detail"]


def test_a_template_the_worker_cannot_read_is_a_422_with_its_message(client: TestClient, worker: dict) -> None:
    worker["error"] = TemplateExtractionError("Balise invalide : {% for e in %}")
    response = create(client, "Décision E")
    assert response.status_code == 422 and "Balise invalide" in response.json()["detail"]


def test_an_unavailable_worker_is_a_503(client: TestClient, worker: dict) -> None:
    worker["error"] = RenderWorkerUnavailableError()
    assert create(client, "Décision F").status_code == 503


def test_a_too_large_file_is_refused(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.routers.admin_document_templates.MAX_TEMPLATE_BYTES", 10)
    assert client.post(f"{URL}/inspect", files={"file": ("m.odt", odt("a"), ODT_MIME)}).status_code == 422


# --- Définition des champs ---


@pytest.mark.parametrize(
    "bad",
    [
        field("a b"),
        field("1abc"),
        field("loop"),
        field("nom", type="image"),
        {"name": "nom", "label": "N", "source": {"kind": "dossier_metadata", "key": "inconnue"}},
        {"name": "nom", "label": "N", "source": {"kind": "analysis", "element_kind": "autre", "definition_name": "x"}},
        {"name": "nom", "label": "N", "source": {"kind": "analysis", "element_kind": "entity"}},
        {"name": "nom", "label": "  ", "source": {"kind": "instruction"}},
        {"name": "nom", "label": "N"},
    ],
)
def test_an_invalid_field_definition_is_refused(client: TestClient, bad: dict) -> None:
    assert create(client, "Décision G", ("nom",), [bad]).status_code == 422


def test_two_fields_with_the_same_name_are_refused(client: TestClient) -> None:
    response = create(client, "Décision H", ("nom",), [field("nom"), field("nom")])
    assert response.status_code == 422 and "plusieurs fois" in json.dumps(response.json(), ensure_ascii=False)


def test_the_fields_must_be_valid_json(client: TestClient) -> None:
    response = client.post(
        URL,
        data={"analyse_id": CURRENT["analyse_id"], "name": "X", "fields": "pas du json"},
        files={"file": ("m.odt", odt(), ODT_MIME)},
    )
    assert response.status_code == 422


def test_a_template_name_is_unique_ignoring_case(client: TestClient) -> None:
    assert create(client, "Courrier unique").status_code == 201
    assert create(client, "  COURRIER UNIQUE ").status_code == 409


# --- Versions : ajout seul, restauration ---


def test_editing_the_definition_adds_a_version_and_keeps_the_file(client: TestClient, worker: dict) -> None:
    template = create(client, "Décision I", ("nom",)).json()
    calls = worker["calls"]

    response = new_version(client, template["id"], "Décision I bis", [field("nom", label="Nom complet")])

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["version_number"] == 2 and body["name"] == n("Décision I bis")
    assert body["fields"][0]["label"] == "Nom complet"
    assert worker["calls"] == calls  # pas de nouvelle lecture : le fichier est inchangé
    versions = client.get(f"{URL}/{template['id']}/versions").json()
    assert [v["version_number"] for v in versions] == [1, 2]
    assert (
        versions[0]["name"] == n("Décision I") and versions[0]["fields"][0]["label"] == "Nom"
    )  # l'ancienne reste intacte
    assert (
        client.get(f"{URL}/{template['id']}/versions/2/file").content
        == client.get(f"{URL}/{template['id']}/versions/1/file").content
    )


def test_a_new_file_adds_a_version_with_its_own_file(client: TestClient) -> None:
    template = create(client, "Décision J", ("nom",)).json()
    response = new_version(client, template["id"], "Décision J", [field("nom"), field("motif")], odt("nom", "motif"))
    assert response.status_code == 201 and response.json()["placeholders"] == ["motif", "nom"]
    v1 = zipfile.ZipFile(io.BytesIO(client.get(f"{URL}/{template['id']}/versions/1/file").content)).read("content.xml")
    v2 = zipfile.ZipFile(io.BytesIO(client.get(f"{URL}/{template['id']}/versions/2/file").content)).read("content.xml")
    assert b"motif" not in v1 and b"motif" in v2


def test_a_version_that_does_not_match_the_file_is_refused_and_nothing_changes(client: TestClient) -> None:
    template = create(client, "Décision K", ("nom",)).json()
    response = new_version(client, template["id"], "Décision K", [field("nom"), field("motif")])
    assert response.status_code == 422 and response.json()["detail"]["unused_fields"] == ["motif"]
    assert client.get(f"{URL}/{template['id']}").json()["version_number"] == 1


def test_restoring_adds_a_version_with_the_old_content_and_file(client: TestClient) -> None:
    template = create(client, "Décision L", ("nom",), description="d1").json()
    v1_id = client.get(f"{URL}/{template['id']}/versions").json()[0]["id"]
    new_version(client, template["id"], "Décision L v2", [field("nom"), field("motif")], odt("nom", "motif"))

    response = client.post(f"{URL}/{template['id']}/restore", json={"version_id": v1_id})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["version_number"] == 3 and body["name"] == n("Décision L") and body["description"] == "d1"
    assert [f["name"] for f in body["fields"]] == ["nom"] and body["placeholders"] == ["nom"]
    versions = client.get(f"{URL}/{template['id']}/versions").json()
    assert len(versions) == 3 and versions[2]["restored_from_version_id"] == v1_id
    restored = zipfile.ZipFile(io.BytesIO(client.get(f"{URL}/{template['id']}/versions/3/file").content))
    assert b"motif" not in restored.read("content.xml")


def test_restoring_an_unknown_version_is_404(client: TestClient) -> None:
    template = create(client, "Décision M").json()
    response = client.post(
        f"{URL}/{template['id']}/restore", json={"version_id": "00000000-0000-0000-0000-000000000000"}
    )
    assert response.status_code == 404


def test_restoring_is_refused_when_the_name_was_taken_since(client: TestClient) -> None:
    first = create(client, "Nom repris").json()
    v1_id = client.get(f"{URL}/{first['id']}/versions").json()[0]["id"]
    new_version(client, first["id"], "Nom libéré", [field("nom")])
    create(client, "Nom repris")  # un autre modèle prend le nom libéré
    assert client.post(f"{URL}/{first['id']}/restore", json={"version_id": v1_id}).status_code == 409


def test_a_rename_to_the_name_of_another_template_is_refused(client: TestClient) -> None:
    create(client, "Déjà pris")
    other = create(client, "Autre nom").json()
    assert new_version(client, other["id"], "déjà pris", [field("nom")]).status_code == 409


# --- Archivage ---


def test_archiving_hides_the_template_and_blocks_edits_until_unarchived(client: TestClient) -> None:
    template = create(client, "Décision N").json()
    archived = client.post(f"{URL}/{template['id']}/archive")
    assert archived.status_code == 200 and archived.json()["archived"] is True
    assert template["id"] not in [t["id"] for t in client.get(URL).json()]
    assert template["id"] in [t["id"] for t in client.get(URL, params={"include_archived": True}).json()]
    assert new_version(client, template["id"], "Décision N", [field("nom")]).status_code == 409

    assert client.post(f"{URL}/{template['id']}/unarchive").json()["archived"] is False
    assert new_version(client, template["id"], "Décision N", [field("nom")]).status_code == 201


# --- Droits ---


def test_every_route_is_forbidden_for_a_non_admin(client: TestClient) -> None:
    template = create(client, "Décision O").json()

    def as_non_admin() -> RequestContext:
        return RequestContext(user_id="regular", email="r@example.com", roles=[], is_admin=False)

    app.dependency_overrides[get_current_user] = as_non_admin
    try:
        tid = template["id"]
        calls = [
            client.get(URL),
            client.get(f"{URL}/{tid}"),
            client.get(f"{URL}/{tid}/versions"),
            client.get(f"{URL}/{tid}/versions/1/file"),
            client.post(f"{URL}/inspect", files={"file": ("m.odt", odt(), ODT_MIME)}),
            client.post(
                URL,
                data={"analyse_id": CURRENT["analyse_id"], "name": "X", "fields": "[]"},
                files={"file": ("m.odt", odt(), ODT_MIME)},
            ),
            client.post(
                f"{URL}/{tid}/versions", data={"analyse_id": CURRENT["analyse_id"], "name": "X", "fields": "[]"}
            ),
            client.post(f"{URL}/{tid}/restore", json={"version_id": "00000000-0000-0000-0000-000000000000"}),
            client.post(f"{URL}/{tid}/archive"),
            client.post(f"{URL}/{tid}/unarchive"),
        ]
        assert [c.status_code for c in calls] == [403] * len(calls)
    finally:
        del app.dependency_overrides[get_current_user]


# --- Un modèle appartient à une analyse (issue #139) ---


def analysis_source(kind: str, name: str) -> dict[str, Any]:
    return {"kind": "analysis", "element_kind": kind, "definition_name": name}


def test_a_template_belongs_to_one_analysis(client: TestClient, analyse: str) -> None:
    body = create(client, "Décision P").json()
    assert body["analyse_id"] == analyse
    assert client.get(f"{URL}/{body['id']}").json()["analyse_id"] == analyse
    # L'analyse ne peut pas changer : ni la création d'une version ni la restauration n'en déplacent un.
    assert new_version(client, body["id"], "Décision P", [field("nom")]).json()["analyse_id"] == analyse


def test_the_analysis_is_required_and_must_exist(client: TestClient) -> None:
    files = {"file": ("m.odt", odt("nom"), ODT_MIME)}
    missing = client.post(URL, data={"name": "X", "fields": json.dumps([field("nom")])}, files=files)
    assert missing.status_code == 422
    unknown = client.post(
        URL, data={"analyse_id": str(uuid.uuid4()), "name": "X", "fields": json.dumps([field("nom")])}, files=files
    )
    assert unknown.status_code == 404 and "Analyse" in unknown.json()["detail"]


def test_the_list_can_be_filtered_by_analysis(client: TestClient, analyse: str) -> None:
    mine = create(client, "Décision Q").json()
    other_analyse = make_analyse(client)
    theirs = client.post(
        URL,
        data={"analyse_id": other_analyse, "name": n("Décision R"), "fields": json.dumps([field("nom")])},
        files={"file": ("m.odt", odt("nom"), ODT_MIME)},
    ).json()

    in_mine = [t["id"] for t in client.get(URL, params={"analyse_id": analyse}).json()]
    in_theirs = [t["id"] for t in client.get(URL, params={"analyse_id": other_analyse}).json()]

    assert in_mine == [mine["id"]] and in_theirs == [theirs["id"]]


def test_the_name_is_unique_within_an_analysis_not_across_analyses(client: TestClient) -> None:
    assert create(client, "Courrier commun").status_code == 201
    assert create(client, "courrier COMMUN").status_code == 409  # même analyse
    other = make_analyse(client)
    files = {"file": ("m.odt", odt("nom"), ODT_MIME)}
    same_name_elsewhere = client.post(
        URL,
        data={"analyse_id": other, "name": n("Courrier commun"), "fields": json.dumps([field("nom")])},
        files=files,
    )
    assert same_name_elsewhere.status_code == 201


def test_a_source_must_designate_an_element_the_analysis_defines(client: TestClient) -> None:
    fields = [
        field("a", source=analysis_source("entity", "SIRET")),  # entité que l'analyse ne définit pas
        field("b", source=analysis_source("classification", "Permis")),  # label inconnu
        field("c", source=analysis_source("synthesis", "Rapport")),  # agent inconnu
        field("d", source=analysis_source("entity", "nom")),  # connue
    ]
    response = create(client, "Décision S", ("a", "b", "c", "d"), fields)
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "ne définit pas" in detail["message"]
    assert [u["field"] for u in detail["unknown_sources"]] == ["a", "b", "c"]
    assert detail["unknown_sources"][0] == {"field": "a", "element_kind": "entity", "definition_name": "SIRET"}


def test_known_elements_are_accepted_whatever_their_case_and_kind(client: TestClient) -> None:
    fields = [
        field("a", source=analysis_source("entity", "NOM")),
        field("b", source=analysis_source("classification", "passeport")),
        field("c", source=analysis_source("synthesis", "synthèse")),
        field("d", source=analysis_source("relation", "n'importe quelle relation")),  # pas de définition à vérifier
        field("e", source=analysis_source("field", "décision")),  # champ renseigné : idem
    ]
    assert create(client, "Décision T", ("a", "b", "c", "d", "e"), fields).status_code == 201


def test_a_new_version_is_checked_against_the_analysis_too(client: TestClient) -> None:
    template = create(client, "Décision U").json()
    bad = new_version(
        client, template["id"], "Décision U", [field("nom", source=analysis_source("entity", "inconnue"))]
    )
    assert bad.status_code == 422 and bad.json()["detail"]["unknown_sources"][0]["field"] == "nom"
    assert client.get(f"{URL}/{template['id']}").json()["version_number"] == 1
    good = new_version(
        client, template["id"], "Décision U", [field("nom", source=analysis_source("entity", "adresse"))]
    )
    assert good.status_code == 201


def test_the_definitions_of_an_analysis_are_offered_as_choices(client: TestClient, analyse: str) -> None:
    response = client.get(f"{URL}/analyses/{analyse}/definitions")
    assert response.status_code == 200
    assert response.json() == {"entity": ["nom", "adresse"], "classification": ["Passeport"], "synthesis": ["Synthèse"]}
    assert client.get(f"{URL}/analyses/{uuid.uuid4()}/definitions").status_code == 404


def test_deleting_an_analysis_deletes_its_templates_and_their_files(client: TestClient, analyse: str) -> None:
    from app.connectors import s3_connector
    from app.db import async_session_factory
    from app.repositories.analyse_repository import AnalyseRepository

    template = create(client, "Décision V").json()
    key = f"document-templates/{template['id']}/v1.odt"
    assert s3_connector.download(key)[0]

    async def delete() -> None:
        async with async_session_factory() as session:
            repository = AnalyseRepository(session)
            await repository.delete(await repository.get(uuid.UUID(analyse)))

    client.portal.call(delete)

    assert client.get(f"{URL}/{template['id']}").status_code == 404
    with pytest.raises(Exception):  # noqa: B017, PT011 - le fichier du modèle a été supprimé avec lui
        s3_connector.download(key)
