"""Colonnes personnalisées du suivi (issue #173) : définitions versionnées, valeurs validées et tracées, filtres,
tri."""

import json
import uuid

import pytest
from fastapi.testclient import TestClient

from tests.access_support import As
from tests.test_dossier_access import _create


def _analyse(client: TestClient) -> dict:
    return client.post("/api/analyses", json={"name": f"Colonnes {uuid.uuid4().hex[:6]}", "description": "T"}).json()


def _field(name: str = "Montant", type_: str = "amount", **extra) -> dict:
    return {"name": name, "type": type_, **extra}


def _put_fields(client: TestClient, analyse_id: str, fields: list[dict], purge: bool = False):
    return client.put(f"/api/analyses/{analyse_id}/custom-fields", json={"fields": fields, "purge_removed": purge})


def _fields_of(client: TestClient, analyse_id: str) -> list[dict]:
    return client.get(f"/api/analyses/{analyse_id}/custom-fields").json()


@pytest.fixture
def analyse(client: TestClient) -> dict:
    return _analyse(client)


@pytest.fixture
def board(client: TestClient, analyse: dict) -> dict:
    """Une analyse avec une colonne de chaque type, et leurs identifiants par nom."""
    fields = [
        _field("Texte", "text"),
        _field("Nombre", "number"),
        _field("Montant", "amount", currency="USD"),
        _field("Date", "date"),
        _field("Prioritaire", "boolean"),
        _field("Service", "choice", choices=["Culture", "Sport", "Social"]),
    ]
    response = _put_fields(client, analyse["id"], fields)
    assert response.status_code == 200, response.text
    ids = {f["name"]: f["id"] for f in response.json()["custom_fields"]}
    return {"analyse": analyse, "ids": ids}


def _dossier(client: TestClient, analyse: dict, name: str = "Dossier") -> dict:
    return client.post("/api/dossiers", json={"name": name, "analyse_id": analyse["id"]}).json()


def _set(client: TestClient, dossier_id: str, field_id: str, value):
    return client.put(f"/api/dossiers/{dossier_id}/custom-values/{field_id}", json={"value": value})


def _row(client: TestClient, analyse_id: str, dossier_id: str) -> dict:
    items = client.get("/api/tracking", params={"analyse_id": analyse_id, "page_size": 100}).json()["items"]
    return next(r for r in items if r["id"] == dossier_id)


# --- Définitions ---


def test_an_administrator_defines_the_columns_and_ids_are_assigned(client: TestClient, analyse: dict) -> None:
    response = _put_fields(
        client,
        analyse["id"],
        [_field("Montant", definition="Montant demandé"), _field("Service", "choice", choices=["A", " B ", "", "A2"])],
    )

    assert response.status_code == 200
    fields = response.json()["custom_fields"]
    assert [f["name"] for f in fields] == ["Montant", "Service"]
    assert all(f["id"].startswith("f_") for f in fields) and fields[0]["id"] != fields[1]["id"]
    assert fields[0]["definition"] == "Montant demandé" and fields[0]["currency"] == "EUR"
    assert fields[1]["choices"] == ["A", "B", "A2"]  # nettoyés
    assert _fields_of(client, analyse["id"]) == fields


def test_only_administrators_define_the_columns(client: TestClient, analyse: dict, world: dict) -> None:
    with As(world["alice"]):
        assert _put_fields(client, analyse["id"], [_field()]).status_code == 403
        assert client.post(f"/api/analyses/{analyse['id']}/custom-fields/restore/{uuid.uuid4()}").status_code == 403
        assert _fields_of(client, analyse["id"]) == []  # la lecture reste ouverte


@pytest.mark.parametrize(
    "fields",
    [
        [_field("")],
        [_field("   ")],
        [_field("A"), _field("a")],  # même nom, sans tenir compte de la casse
        [_field("Choix", "choice")],  # une liste de choix sans choix
        [_field("Choix", "choice", choices=["x", "x"])],
        [_field("Montant", "amount", default_value=-5)],  # défaut qui ne convient pas au type
        [_field("Date", "date", default_value="demain")],
        [_field("Service", "choice", choices=["A"], default_value="B")],
        [_field("Montant", "amount", currency="CHF")],
        [_field("Type", "image")],
        [_field("Trop long " + "x" * 80)],
        [_field(f"Champ {i}") for i in range(21)],  # plus de 20 champs
        [{**_field("Mauvais id"), "id": "pas-un-id"}],
    ],
)
def test_invalid_definitions_are_refused(client: TestClient, analyse: dict, fields: list[dict]) -> None:
    assert _put_fields(client, analyse["id"], fields).status_code == 422
    assert _fields_of(client, analyse["id"]) == []


def test_twenty_fields_are_allowed(client: TestClient, analyse: dict) -> None:
    assert _put_fields(client, analyse["id"], [_field(f"Champ {i}", "text") for i in range(20)]).status_code == 200


def test_every_change_is_versioned_and_restorable(client: TestClient, analyse: dict) -> None:
    first_response = _put_fields(client, analyse["id"], [_field("Montant")]).json()
    first = first_response["custom_fields"]
    again = _put_fields(client, analyse["id"], first).json()  # inchangé : pas de version inutile
    second = _put_fields(client, analyse["id"], [{**first[0], "name": "Montant demandé"}]).json()

    # L'état précédent est conservé à chaque changement : d'abord « aucun champ », puis « Montant ».
    assert [v["content"] for v in first_response["custom_fields_versions"]] == [[]]
    assert len(again["custom_fields_versions"]) == 1
    assert [[f["name"] for f in v["content"]] for v in reversed(second["custom_fields_versions"])] == [[], ["Montant"]]

    version_id = next(v["id"] for v in second["custom_fields_versions"] if v["content"])
    restored = client.post(f"/api/analyses/{analyse['id']}/custom-fields/restore/{version_id}").json()

    assert restored["custom_fields"][0]["name"] == "Montant" and restored["custom_fields"][0]["id"] == first[0]["id"]
    assert len(restored["custom_fields_versions"]) == 3  # l'état courant est devenu une version : rien d'écrasé
    assert client.post(f"/api/analyses/{analyse['id']}/custom-fields/restore/{uuid.uuid4()}").status_code == 404


def test_an_existing_id_is_kept_when_a_field_is_renamed(client: TestClient, analyse: dict) -> None:
    created = _put_fields(client, analyse["id"], [_field("Montant")]).json()["custom_fields"][0]

    renamed = _put_fields(client, analyse["id"], [{**created, "name": "Somme"}]).json()["custom_fields"][0]

    assert renamed["id"] == created["id"] and renamed["name"] == "Somme"


# --- Valeurs ---


def test_set_change_and_clear_a_value(client: TestClient, board: dict) -> None:
    dossier = _dossier(client, board["analyse"])
    montant = board["ids"]["Montant"]

    saved = _set(client, dossier["id"], montant, 1500.5)
    changed = _set(client, dossier["id"], montant, 2000)
    cleared = _set(client, dossier["id"], montant, "")

    assert saved.status_code == 200 and saved.json() == {"field_id": montant, "value": 1500.5}
    assert changed.json()["value"] == 2000
    assert cleared.json()["value"] is None
    assert montant not in client.get(f"/api/dossiers/{dossier['id']}").json()["custom_values"]


@pytest.mark.parametrize(
    ("name", "value", "message"),
    [
        ("Montant", -5, "Saisissez un montant positif."),
        ("Nombre", "douze", "Saisissez un nombre."),
        ("Date", "2026-13-01", "Saisissez une date valide."),
        ("Service", "Inconnu", "Choisissez une valeur de la liste."),
        ("Prioritaire", "oui", "Valeur invalide."),
    ],
)
def test_invalid_values_are_refused_with_the_message_to_show(
    client: TestClient, board: dict, name: str, value, message: str
) -> None:
    dossier = _dossier(client, board["analyse"])

    response = _set(client, dossier["id"], board["ids"][name], value)

    assert response.status_code == 422
    assert response.json()["detail"] == {"code": "invalid_value", "message": message}
    assert client.get(f"/api/dossiers/{dossier['id']}").json()["custom_values"] == {}


def test_a_required_field_cannot_be_cleared(client: TestClient, analyse: dict) -> None:
    field = _put_fields(client, analyse["id"], [_field("Service", "choice", choices=["A"], required=True)]).json()[
        "custom_fields"
    ][0]
    dossier = _dossier(client, analyse)
    _set(client, dossier["id"], field["id"], "A")

    cleared = _set(client, dossier["id"], field["id"], None)

    assert cleared.status_code == 422 and cleared.json()["detail"]["message"] == "Ce champ est obligatoire."


def test_an_unknown_field_or_a_dossier_without_analyse_is_404(client: TestClient, board: dict, world: dict) -> None:
    dossier = _dossier(client, board["analyse"])
    with As(world["alice"]):
        loose = client.post("/api/dossiers", json={"name": "À ranger"}).json()

    assert _set(client, dossier["id"], "f_inconnu0", 1).status_code == 404
    assert _set(client, dossier["id"], board["ids"]["Montant"], 1).status_code == 200
    with As(world["alice"]):
        assert _set(client, loose["id"], board["ids"]["Montant"], 1).status_code == 404


def test_a_value_is_traced_with_old_and_new_and_author(client: TestClient, board: dict) -> None:
    dossier = _dossier(client, board["analyse"])
    montant = board["ids"]["Montant"]

    _set(client, dossier["id"], montant, 100)
    _set(client, dossier["id"], montant, 100)  # inchangé : rien de plus
    _set(client, dossier["id"], montant, 250)
    events = client.get(f"/api/dossiers/{dossier['id']}/events", params={"type": "custom_value_changed"}).json()[
        "items"
    ]

    assert [(e["payload"]["from"], e["payload"]["to"]) for e in reversed(events)] == [(None, 100), (100, 250)]
    assert events[0]["payload"]["field"] == {"id": montant, "name": "Montant"}
    assert events[0]["actor_id"] == "dev-user"


def test_values_follow_the_dossier_access(client: TestClient, board: dict, world: dict) -> None:
    with As(world["alice"]):
        dossier = _create(client, board["analyse"])  # restreint à /a
    with As(world["bob"]):
        assert _set(client, dossier["id"], board["ids"]["Montant"], 1).status_code == 404


def test_new_dossiers_receive_the_default_values(client: TestClient, analyse: dict) -> None:
    fields = _put_fields(
        client,
        analyse["id"],
        [
            _field("Service", "choice", choices=["Culture", "Sport"], default_value="Culture"),
            _field("Prioritaire", "boolean", default_value=False),
            _field("Montant", "amount"),
        ],
    ).json()["custom_fields"]
    ids = {f["name"]: f["id"] for f in fields}

    dossier = _dossier(client, analyse)

    assert dossier["custom_values"] == {ids["Service"]: "Culture", ids["Prioritaire"]: False}


# --- Suppression et changement de type ---


def test_a_removed_field_keeps_its_values_until_purged_or_restored(client: TestClient, board: dict) -> None:
    analyse = board["analyse"]
    montant = board["ids"]["Montant"]
    dossier = _dossier(client, analyse)
    _set(client, dossier["id"], montant, 300)
    kept = [f for f in _fields_of(client, analyse["id"]) if f["id"] != montant]

    without = _put_fields(client, analyse["id"], kept).json()

    assert montant in client.get(f"/api/dossiers/{dossier['id']}").json()["custom_values"]  # conservée en base
    assert montant not in _row(client, analyse["id"], dossier["id"])["values"]  # mais plus affichée
    restored = client.post(
        f"/api/analyses/{analyse['id']}/custom-fields/restore/{without['custom_fields_versions'][0]['id']}"
    ).json()
    assert _row(client, analyse["id"], dossier["id"])["values"][montant] == 300  # le champ revient avec sa valeur
    assert any(f["id"] == montant for f in restored["custom_fields"])


def test_purging_a_removed_field_deletes_its_values_everywhere(client: TestClient, board: dict) -> None:
    analyse = board["analyse"]
    montant, texte = board["ids"]["Montant"], board["ids"]["Texte"]
    dossier = _dossier(client, analyse)
    _set(client, dossier["id"], montant, 300)
    _set(client, dossier["id"], texte, "à garder")
    kept = [f for f in _fields_of(client, analyse["id"]) if f["id"] != montant]

    _put_fields(client, analyse["id"], kept, purge=True)

    assert client.get(f"/api/dossiers/{dossier['id']}").json()["custom_values"] == {texte: "à garder"}


def test_changing_the_type_of_a_field_drops_its_values(client: TestClient, board: dict) -> None:
    analyse = board["analyse"]
    nombre, texte = board["ids"]["Nombre"], board["ids"]["Texte"]
    dossier = _dossier(client, analyse)
    _set(client, dossier["id"], nombre, 42)
    _set(client, dossier["id"], texte, "reste")
    fields = [{**f, "type": "text"} if f["id"] == nombre else f for f in _fields_of(client, analyse["id"])]

    assert _put_fields(client, analyse["id"], fields).status_code == 200

    assert client.get(f"/api/dossiers/{dossier['id']}").json()["custom_values"] == {texte: "reste"}


# --- Suivi : valeurs, filtres, tri, recherche ---


def _tracked(client: TestClient, analyse_id: str, **params) -> list[str]:
    response = client.get("/api/tracking", params={"analyse_id": analyse_id, "page_size": 100, **params})
    assert response.status_code == 200, response.text
    return [r["name"] for r in response.json()["items"]]


def _filter(client: TestClient, analyse_id: str, spec: dict, **params) -> list[str]:
    return _tracked(client, analyse_id, field_filters=json.dumps(spec), sort="name", direction="asc", **params)


@pytest.fixture
def filled(client: TestClient, board: dict) -> dict:
    """Trois dossiers aux valeurs différentes."""
    ids, analyse = board["ids"], board["analyse"]
    rows = {
        "Alpha": {
            "Texte": "Association Les Mouettes",
            "Nombre": 5,
            "Montant": 1000,
            "Date": "2026-03-01",
            "Prioritaire": True,
            "Service": "Culture",
        },
        "Beta": {
            "Texte": "Convention sportive",
            "Nombre": 15,
            "Montant": 250.5,
            "Date": "2026-06-15",
            "Prioritaire": False,
            "Service": "Sport",
        },
        "Gamma": {},
    }
    for name, values in rows.items():
        dossier = _dossier(client, analyse, name)
        for label, value in values.items():
            assert _set(client, dossier["id"], ids[label], value).status_code == 200
    return board


def test_tracking_rows_carry_the_current_values(client: TestClient, filled: dict) -> None:
    items = client.get("/api/tracking", params={"analyse_id": filled["analyse"]["id"], "search": "Alpha"}).json()[
        "items"
    ]

    assert items[0]["values"][filled["ids"]["Montant"]] == 1000
    assert items[0]["values"][filled["ids"]["Prioritaire"]] is True


def test_filter_by_text_choice_and_boolean(client: TestClient, filled: dict) -> None:
    ids, analyse = filled["ids"], filled["analyse"]["id"]

    assert _filter(client, analyse, {ids["Texte"]: "mouettes"}) == ["Alpha"]  # sans tenir compte de la casse
    assert _filter(client, analyse, {ids["Texte"]: "100%"}) == []  # « % » n'est pas un joker
    assert _filter(client, analyse, {ids["Service"]: "Sport"}) == ["Beta"]
    assert _filter(client, analyse, {ids["Prioritaire"]: "true"}) == ["Alpha"]
    assert _filter(client, analyse, {ids["Prioritaire"]: "false"}) == [
        "Beta",
        "Gamma",
    ]  # « non » inclut « sans valeur »


def test_filter_by_number_amount_and_date_ranges(client: TestClient, filled: dict) -> None:
    ids, analyse = filled["ids"], filled["analyse"]["id"]

    assert _filter(client, analyse, {ids["Nombre"]: {"min": "10", "max": ""}}) == ["Beta"]
    assert _filter(client, analyse, {ids["Nombre"]: {"min": "5", "max": "15"}}) == ["Alpha", "Beta"]  # bornes incluses
    assert _filter(client, analyse, {ids["Montant"]: {"min": "", "max": "300"}}) == ["Beta"]
    assert _filter(client, analyse, {ids["Montant"]: {"min": "1000,0", "max": ""}}) == ["Alpha"]  # virgule française
    assert _filter(client, analyse, {ids["Date"]: {"min": "2026-04-01", "max": ""}}) == ["Beta"]
    assert _filter(client, analyse, {ids["Date"]: {"min": "2026-03-01", "max": "2026-03-01"}}) == ["Alpha"]


def test_filters_combine_and_work_with_the_other_filters(client: TestClient, filled: dict) -> None:
    ids, analyse = filled["ids"], filled["analyse"]["id"]

    assert _filter(client, analyse, {ids["Service"]: "Sport", ids["Nombre"]: {"min": "10", "max": ""}}) == ["Beta"]
    assert _filter(client, analyse, {ids["Service"]: "Sport", ids["Nombre"]: {"min": "", "max": "10"}}) == []
    assert _filter(client, analyse, {ids["Service"]: "Sport"}, assignee="none") == ["Beta"]
    assert _filter(client, analyse, {ids["Service"]: "Sport"}, assignee="me") == []


def test_search_also_looks_in_the_values(client: TestClient, filled: dict) -> None:
    analyse = filled["analyse"]["id"]

    assert _tracked(client, analyse, search="sportive") == ["Beta"]  # une valeur de texte
    assert _tracked(client, analyse, search="Culture") == ["Alpha"]  # une valeur de liste
    assert sorted(_tracked(client, analyse, search="Alpha")) == ["Alpha"]  # et toujours le nom


def test_sort_by_a_column_puts_missing_values_last_in_both_directions(client: TestClient, filled: dict) -> None:
    ids, analyse = filled["ids"], filled["analyse"]["id"]

    def order(key: str, direction: str) -> list[str]:
        return _tracked(client, analyse, sort="field", sort_field=ids[key], direction=direction)

    assert order("Montant", "asc") == ["Beta", "Alpha", "Gamma"]
    assert order("Montant", "desc") == ["Alpha", "Beta", "Gamma"]
    assert order("Nombre", "asc") == ["Alpha", "Beta", "Gamma"]  # numérique : 5 avant 15, pas « 15 » avant « 5 »
    assert order("Date", "desc") == ["Beta", "Alpha", "Gamma"]
    assert order("Texte", "asc") == ["Alpha", "Beta", "Gamma"]


def test_custom_columns_need_exactly_one_analyse(client: TestClient, filled: dict) -> None:
    ids = filled["ids"]
    other = _analyse(client)

    no_analyse = client.get("/api/tracking", params={"field_filters": json.dumps({ids["Texte"]: "x"})})
    two = client.get(
        "/api/tracking",
        params={"analyse_id": [filled["analyse"]["id"], other["id"]], "sort": "field", "sort_field": ids["Texte"]},
    )

    assert no_analyse.status_code == 422 and no_analyse.json()["detail"]["code"] == "single_analyse_required"
    assert two.status_code == 422 and two.json()["detail"]["code"] == "single_analyse_required"


def test_unknown_columns_and_invalid_filters_are_refused(client: TestClient, filled: dict) -> None:
    analyse = filled["analyse"]["id"]
    base = {"analyse_id": analyse}

    unknown_filter = client.get("/api/tracking", params={**base, "field_filters": json.dumps({"f_inconnu0": "x"})})
    bad_json = client.get("/api/tracking", params={**base, "field_filters": "{pas du json"})
    bad_range = client.get(
        "/api/tracking", params={**base, "field_filters": json.dumps({filled["ids"]["Nombre"]: {"min": "abc"}})}
    )
    unknown_sort = client.get("/api/tracking", params={**base, "sort": "field", "sort_field": "f_inconnu0"})
    no_sort_field = client.get("/api/tracking", params={**base, "sort": "field"})

    assert unknown_filter.status_code == bad_json.status_code == bad_range.status_code == 422
    assert unknown_filter.json()["detail"]["code"] == "invalid_field_filter"
    assert unknown_sort.status_code == no_sort_field.status_code == 422
    assert unknown_sort.json()["detail"]["code"] == "unknown_field"


def test_the_values_of_a_dossier_the_person_cannot_see_are_not_listed(
    client: TestClient, board: dict, world: dict
) -> None:
    ids = board["ids"]
    with As(world["alice"]):
        dossier = _create(client, board["analyse"])
        _set(client, dossier["id"], ids["Texte"], "confidentiel")
    with As(world["bob"]):
        by_value = _tracked(client, board["analyse"]["id"], search="confidentiel")
        by_filter = _filter(client, board["analyse"]["id"], {ids["Texte"]: "confidentiel"})

    assert by_value == [] and by_filter == []
