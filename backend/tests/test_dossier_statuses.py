"""Statuts de dossier par analyse et date de clôture (issue #168)."""

import uuid

from fastapi.testclient import TestClient


def _create_analyse(client: TestClient, name: str) -> dict:
    return client.post("/api/analyses", json={"name": name, "description": "Test"}).json()


def _create_dossier(client: TestClient, analyse_id: str | None, name: str = "Dossier statuts") -> dict:
    payload = {"name": name}
    if analyse_id:
        payload["analyse_id"] = analyse_id
    return client.post("/api/dossiers", json=payload).json()


def _status_in(status: dict, **changes) -> dict:
    """Entrée de mise à jour qui conserve l'identité d'un statut existant."""
    entry = {
        "id": status["id"],
        "name": status["name"],
        "color": status["color"],
        "is_initial": status["is_initial"],
        "is_final": status["is_final"],
    }
    return {**entry, **changes}


def _put_statuses(client: TestClient, analyse_id: str, statuses: list[dict], replacements: dict | None = None):
    return client.put(
        f"/api/analyses/{analyse_id}/statuses",
        json={"statuses": statuses, "replacements": replacements or {}},
    )


# --- Statuts par défaut ---


def test_new_analyse_has_default_statuses(client: TestClient) -> None:
    analyse = _create_analyse(client, "Statuts par défaut")
    statuses = analyse["statuses"]

    assert [s["position"] for s in statuses] == list(range(len(statuses)))
    assert sum(s["is_initial"] for s in statuses) == 1
    assert any(s["is_final"] for s in statuses)
    assert client.get(f"/api/analyses/{analyse['id']}/statuses").json() == statuses


def test_list_statuses_of_unknown_analyse_is_404(client: TestClient) -> None:
    assert client.get(f"/api/analyses/{uuid.uuid4()}/statuses").status_code == 404


# --- Statut d'un dossier ---


def test_new_dossier_receives_the_initial_status(client: TestClient) -> None:
    analyse = _create_analyse(client, "Statut initial")
    initial = next(s for s in analyse["statuses"] if s["is_initial"])

    dossier = _create_dossier(client, analyse["id"])

    assert dossier["workflow_status"]["id"] == initial["id"]
    assert dossier["closed_at"] is None


def test_dossier_without_analyse_has_no_status(client: TestClient) -> None:
    dossier = _create_dossier(client, None, "Dossier à ranger")
    assert dossier["workflow_status"] is None
    assert dossier["closed_at"] is None


def test_assigning_an_analyse_gives_the_initial_status(client: TestClient) -> None:
    analyse = _create_analyse(client, "Rattachement")
    initial = next(s for s in analyse["statuses"] if s["is_initial"])
    dossier = _create_dossier(client, None, "À ranger puis rattaché")

    assigned = client.post(f"/api/dossiers/{dossier['id']}/assign", json={"analyse_id": analyse["id"]}).json()

    assert assigned["workflow_status"]["id"] == initial["id"]


def test_final_status_sets_closed_at_and_reopening_clears_it(client: TestClient) -> None:
    analyse = _create_analyse(client, "Clôture")
    initial = next(s for s in analyse["statuses"] if s["is_initial"])
    final = next(s for s in analyse["statuses"] if s["is_final"])
    dossier = _create_dossier(client, analyse["id"])

    closed = client.put(f"/api/dossiers/{dossier['id']}/workflow-status", json={"status_id": final["id"]})
    assert closed.status_code == 200
    assert closed.json()["workflow_status"]["id"] == final["id"]
    closed_at = closed.json()["closed_at"]
    assert closed_at is not None

    reopened = client.put(f"/api/dossiers/{dossier['id']}/workflow-status", json={"status_id": initial["id"]}).json()
    assert reopened["workflow_status"]["id"] == initial["id"]
    assert reopened["closed_at"] is None


def test_closed_at_is_kept_between_two_final_statuses(client: TestClient) -> None:
    analyse = _create_analyse(client, "Deux statuts finaux")
    statuses = analyse["statuses"]
    final = next(s for s in statuses if s["is_final"])
    updated = _put_statuses(
        client,
        analyse["id"],
        [_status_in(s) for s in statuses] + [{"name": "Rejeté", "color": "#ce0500", "is_final": True}],
    ).json()
    other_final = next(s for s in updated["statuses"] if s["name"] == "Rejeté")
    dossier = _create_dossier(client, analyse["id"])

    first = client.put(f"/api/dossiers/{dossier['id']}/workflow-status", json={"status_id": final["id"]}).json()
    second = client.put(f"/api/dossiers/{dossier['id']}/workflow-status", json={"status_id": other_final["id"]}).json()

    assert second["closed_at"] == first["closed_at"]


def test_status_of_another_analyse_is_refused(client: TestClient) -> None:
    analyse = _create_analyse(client, "Analyse du dossier")
    other = _create_analyse(client, "Autre analyse")
    dossier = _create_dossier(client, analyse["id"])

    response = client.put(
        f"/api/dossiers/{dossier['id']}/workflow-status", json={"status_id": other["statuses"][0]["id"]}
    )

    assert response.status_code == 400


def test_status_cannot_be_set_on_a_dossier_without_analyse(client: TestClient) -> None:
    analyse = _create_analyse(client, "Source du statut")
    dossier = _create_dossier(client, None, "Sans analyse")

    response = client.put(
        f"/api/dossiers/{dossier['id']}/workflow-status", json={"status_id": analyse["statuses"][0]["id"]}
    )

    assert response.status_code == 400


def test_status_change_on_unknown_dossier_is_404(client: TestClient) -> None:
    response = client.put(f"/api/dossiers/{uuid.uuid4()}/workflow-status", json={"status_id": str(uuid.uuid4())})
    assert response.status_code == 404


# --- Modification de la liste des statuts ---


def test_statuses_can_be_renamed_recolored_and_reordered_keeping_identity(client: TestClient) -> None:
    analyse = _create_analyse(client, "Modification des statuts")
    initial, middle, final = analyse["statuses"]

    response = _put_statuses(
        client,
        analyse["id"],
        [
            _status_in(initial, name="Reçu"),
            _status_in(final, color="#000000"),
            _status_in(middle),
        ],
    )

    assert response.status_code == 200
    updated = response.json()["statuses"]
    assert [s["id"] for s in updated] == [initial["id"], final["id"], middle["id"]]
    assert [s["position"] for s in updated] == [0, 1, 2]
    assert updated[0]["name"] == "Reçu"
    assert updated[1]["color"] == "#000000"


def test_adding_a_status_creates_a_new_identity(client: TestClient) -> None:
    analyse = _create_analyse(client, "Ajout d'un statut")
    statuses = analyse["statuses"]

    response = _put_statuses(
        client, analyse["id"], [_status_in(s) for s in statuses] + [{"name": "En attente de pièces"}]
    )

    updated = response.json()["statuses"]
    assert len(updated) == len(statuses) + 1
    assert {s["id"] for s in statuses} < {s["id"] for s in updated}
    assert updated[-1]["name"] == "En attente de pièces"
    assert updated[-1]["color"] == "#6a6af4"  # couleur par défaut


def test_statuses_must_have_exactly_one_initial(client: TestClient) -> None:
    analyse = _create_analyse(client, "Un seul initial")
    statuses = analyse["statuses"]

    none_initial = _put_statuses(client, analyse["id"], [_status_in(s, is_initial=False) for s in statuses])
    two_initial = _put_statuses(
        client, analyse["id"], [_status_in(s, is_initial=True, is_final=False) for s in statuses]
    )

    assert none_initial.status_code == 422
    assert two_initial.status_code == 422


def test_status_cannot_be_both_initial_and_final(client: TestClient) -> None:
    analyse = _create_analyse(client, "Initial et final")
    first, *rest = analyse["statuses"]

    response = _put_statuses(client, analyse["id"], [_status_in(first, is_final=True), *map(_status_in, rest)])

    assert response.status_code == 422


def test_status_names_must_be_unique_and_not_blank(client: TestClient) -> None:
    analyse = _create_analyse(client, "Noms de statuts")
    first, second, third = analyse["statuses"]

    duplicate = _put_statuses(
        client, analyse["id"], [_status_in(first), _status_in(second, name="  à INSTRUIRE "), _status_in(third)]
    )
    blank = _put_statuses(client, analyse["id"], [_status_in(first), _status_in(second, name="   "), _status_in(third)])

    assert duplicate.status_code == 422
    assert blank.status_code == 422


def test_status_list_cannot_be_empty_and_color_must_be_hex(client: TestClient) -> None:
    analyse = _create_analyse(client, "Liste et couleur")
    first, *rest = analyse["statuses"]

    empty = _put_statuses(client, analyse["id"], [])
    bad_color = _put_statuses(client, analyse["id"], [_status_in(first, color="rouge"), *map(_status_in, rest)])

    assert empty.status_code == 422
    assert bad_color.status_code == 422


def test_unknown_status_id_is_refused(client: TestClient) -> None:
    analyse = _create_analyse(client, "Statut inconnu")
    other = _create_analyse(client, "Statuts d'une autre analyse")
    statuses = analyse["statuses"]

    response = _put_statuses(client, analyse["id"], [_status_in(statuses[0]), _status_in(other["statuses"][1])])

    assert response.status_code == 422


# --- Suppression d'un statut ---


def test_unused_status_can_be_deleted_without_replacement(client: TestClient) -> None:
    analyse = _create_analyse(client, "Suppression libre")
    initial, middle, final = analyse["statuses"]

    response = _put_statuses(client, analyse["id"], [_status_in(initial), _status_in(final)])

    assert response.status_code == 200
    assert [s["id"] for s in response.json()["statuses"]] == [initial["id"], final["id"]]


def test_used_status_requires_a_replacement(client: TestClient) -> None:
    analyse = _create_analyse(client, "Suppression d'un statut utilisé")
    initial, middle, final = analyse["statuses"]
    dossier = _create_dossier(client, analyse["id"])
    client.put(f"/api/dossiers/{dossier['id']}/workflow-status", json={"status_id": middle["id"]})

    response = _put_statuses(client, analyse["id"], [_status_in(initial), _status_in(final)])

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["code"] == "status_in_use"
    assert detail["statuses"] == [{"id": middle["id"], "name": middle["name"], "dossier_count": 1}]
    # Rien n'a changé.
    assert client.get(f"/api/analyses/{analyse['id']}/statuses").json() == analyse["statuses"]


def test_replacement_moves_the_dossiers(client: TestClient) -> None:
    analyse = _create_analyse(client, "Remplacement")
    initial, middle, final = analyse["statuses"]
    dossier = _create_dossier(client, analyse["id"])
    client.put(f"/api/dossiers/{dossier['id']}/workflow-status", json={"status_id": middle["id"]})

    response = _put_statuses(
        client,
        analyse["id"],
        [_status_in(initial), _status_in(final)],
        replacements={middle["id"]: initial["id"]},
    )

    assert response.status_code == 200
    moved = client.get(f"/api/dossiers/{dossier['id']}").json()
    assert moved["workflow_status"]["id"] == initial["id"]
    assert moved["closed_at"] is None


def test_replacement_by_a_final_status_closes_the_dossiers(client: TestClient) -> None:
    analyse = _create_analyse(client, "Remplacement final")
    initial, middle, final = analyse["statuses"]
    dossier = _create_dossier(client, analyse["id"])
    client.put(f"/api/dossiers/{dossier['id']}/workflow-status", json={"status_id": middle["id"]})

    _put_statuses(
        client,
        analyse["id"],
        [_status_in(initial), _status_in(final)],
        replacements={middle["id"]: final["id"]},
    )

    moved = client.get(f"/api/dossiers/{dossier['id']}").json()
    assert moved["workflow_status"]["id"] == final["id"]
    assert moved["closed_at"] is not None


def test_replacement_must_be_a_kept_status(client: TestClient) -> None:
    analyse = _create_analyse(client, "Remplaçant supprimé")
    initial, middle, final = analyse["statuses"]
    dossier = _create_dossier(client, analyse["id"])
    client.put(f"/api/dossiers/{dossier['id']}/workflow-status", json={"status_id": middle["id"]})

    response = _put_statuses(
        client,
        analyse["id"],
        [_status_in(initial), _status_in(final)],
        replacements={middle["id"]: middle["id"]},
    )

    assert response.status_code == 409


# --- Caractère final d'un statut ---


def test_marking_a_status_final_closes_its_dossiers_and_unmarking_reopens_them(client: TestClient) -> None:
    analyse = _create_analyse(client, "Changement du caractère final")
    initial, middle, final = analyse["statuses"]
    dossier = _create_dossier(client, analyse["id"])
    client.put(f"/api/dossiers/{dossier['id']}/workflow-status", json={"status_id": middle["id"]})

    _put_statuses(client, analyse["id"], [_status_in(initial), _status_in(middle, is_final=True), _status_in(final)])
    assert client.get(f"/api/dossiers/{dossier['id']}").json()["closed_at"] is not None

    _put_statuses(client, analyse["id"], [_status_in(initial), _status_in(middle), _status_in(final)])
    assert client.get(f"/api/dossiers/{dossier['id']}").json()["closed_at"] is None


# --- Versionnement ---


def test_statuses_are_versioned_and_restorable(client: TestClient) -> None:
    analyse = _create_analyse(client, "Historique des statuts")
    initial, middle, final = analyse["statuses"]
    assert analyse["statuses_versions"] == []

    updated = _put_statuses(
        client, analyse["id"], [_status_in(initial, name="Reçu"), _status_in(middle), _status_in(final)]
    ).json()
    versions = updated["statuses_versions"]
    assert len(versions) == 1
    assert [s["name"] for s in versions[0]["content"]] == [s["name"] for s in analyse["statuses"]]
    assert [s["id"] for s in versions[0]["content"]] == [s["id"] for s in analyse["statuses"]]

    restored = client.post(f"/api/analyses/{analyse['id']}/statuses/restore/{versions[0]['id']}")

    assert restored.status_code == 200
    body = restored.json()
    assert body["statuses"] == analyse["statuses"]  # mêmes identifiants, noms et positions
    assert len(body["statuses_versions"]) == 2  # l'état « Reçu » est lui-même devenu une version


def test_unchanged_statuses_do_not_create_a_version(client: TestClient) -> None:
    analyse = _create_analyse(client, "Pas de version inutile")

    response = _put_statuses(client, analyse["id"], [_status_in(s) for s in analyse["statuses"]])

    assert response.status_code == 200
    assert response.json()["statuses_versions"] == []


def test_restore_recreates_a_deleted_status_with_its_identity(client: TestClient) -> None:
    analyse = _create_analyse(client, "Restauration d'un statut supprimé")
    initial, middle, final = analyse["statuses"]
    deleted = _put_statuses(client, analyse["id"], [_status_in(initial), _status_in(final)]).json()

    restored = client.post(
        f"/api/analyses/{analyse['id']}/statuses/restore/{deleted['statuses_versions'][0]['id']}"
    ).json()

    assert [s["id"] for s in restored["statuses"]] == [initial["id"], middle["id"], final["id"]]


def test_restore_that_removes_a_used_status_requires_a_replacement(client: TestClient) -> None:
    analyse = _create_analyse(client, "Restauration et dossiers")
    initial, middle, final = analyse["statuses"]
    extra = _put_statuses(
        client, analyse["id"], [_status_in(s) for s in analyse["statuses"]] + [{"name": "Nouveau"}]
    ).json()
    new_status = extra["statuses"][-1]
    dossier = _create_dossier(client, analyse["id"])
    client.put(f"/api/dossiers/{dossier['id']}/workflow-status", json={"status_id": new_status["id"]})
    version_id = extra["statuses_versions"][0]["id"]  # état sans « Nouveau »

    refused = client.post(f"/api/analyses/{analyse['id']}/statuses/restore/{version_id}")
    accepted = client.post(
        f"/api/analyses/{analyse['id']}/statuses/restore/{version_id}",
        json={"replacements": {new_status["id"]: initial["id"]}},
    )

    assert refused.status_code == 409
    assert accepted.status_code == 200
    assert client.get(f"/api/dossiers/{dossier['id']}").json()["workflow_status"]["id"] == initial["id"]


def test_restore_unknown_version_is_404(client: TestClient) -> None:
    analyse = _create_analyse(client, "Version inconnue")
    assert client.post(f"/api/analyses/{analyse['id']}/statuses/restore/{uuid.uuid4()}").status_code == 404


# --- Liste des dossiers : filtre et tri par statut (issue #170) ---


def _list_dossiers(client: TestClient, **params) -> list[dict]:
    """Tous les dossiers de la liste (toutes les pages) : la base de test en contient beaucoup d'autres."""
    items: list[dict] = []
    page = 1
    while True:
        body = client.get("/api/dossiers", params={"page": page, "page_size": 100, **params}).json()
        items += body["items"]
        if page >= body["pages"]:
            return items
        page += 1


def test_list_dossiers_can_be_filtered_by_status(client: TestClient) -> None:
    analyse = _create_analyse(client, "Filtre par statut")
    initial, middle, _final = analyse["statuses"]
    waiting = _create_dossier(client, analyse["id"], "Dossier en attente")
    working = _create_dossier(client, analyse["id"], "Dossier en cours d'instruction")
    client.put(f"/api/dossiers/{working['id']}/workflow-status", json={"status_id": middle["id"]})

    only_initial = {d["id"] for d in _list_dossiers(client, workflow_status_id=initial["id"])}
    only_middle = {d["id"] for d in _list_dossiers(client, workflow_status_id=middle["id"])}

    assert waiting["id"] in only_initial and working["id"] not in only_initial
    assert only_middle == {working["id"]}


def test_list_dossiers_can_be_sorted_by_status_in_the_analyse_order(client: TestClient) -> None:
    analyse = _create_analyse(client, "Tri par statut")
    initial, middle, final = analyse["statuses"]
    first = _create_dossier(client, analyse["id"], "Dossier A")
    second = _create_dossier(client, analyse["id"], "Dossier B")
    third = _create_dossier(client, analyse["id"], "Dossier C")
    client.put(f"/api/dossiers/{first['id']}/workflow-status", json={"status_id": final["id"]})
    client.put(f"/api/dossiers/{second['id']}/workflow-status", json={"status_id": middle["id"]})

    ids = [d["id"] for d in _list_dossiers(client, sort="status") if d["analyse_id"] == analyse["id"]]

    assert ids == [third["id"], second["id"], first["id"]]  # initial, puis intermédiaire, puis final


def test_list_dossiers_sorted_by_status_puts_dossiers_without_status_last(client: TestClient) -> None:
    analyse = _create_analyse(client, "Tri avec dossier à ranger")
    ranged = _create_dossier(client, analyse["id"], "Dossier rangé")
    to_sort = _create_dossier(client, None, "Dossier à ranger")

    items = _list_dossiers(client, sort="status")
    ids = [d["id"] for d in items]

    assert ids.index(ranged["id"]) < ids.index(to_sort["id"])


def test_list_dossiers_rejects_an_unknown_sort(client: TestClient) -> None:
    assert client.get("/api/dossiers", params={"sort": "name"}).status_code == 422


def test_analyse_list_items_carry_their_statuses(client: TestClient) -> None:
    analyse = _create_analyse(client, "Statuts dans la liste")

    items = client.get("/api/analyses", params={"q": "Statuts dans la liste"}).json()["items"]

    listed = next(item for item in items if item["id"] == analyse["id"])
    assert listed["statuses"] == analyse["statuses"]
