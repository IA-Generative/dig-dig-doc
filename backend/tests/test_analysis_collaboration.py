"""Tests du travail à plusieurs sur l'analyse de dossier (issue #118) : verrou court
par élément avec expiration, présence, flux SSE, contrôle de version et écritures
concurrentes."""

import asyncio
import json
import uuid
from collections.abc import Awaitable, Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.factory import RequestContext, get_current_user
from app.db import async_session_factory
from app.main import app
from app.models.dossier_analysis import (
    AnalysisElement,
    AnalysisElementKind,
    DossierAnalysis,
    DossierAnalysisStatus,
    ElementVersionOrigin,
)
from app.repositories import analysis_collaboration_repository as collaboration
from app.repositories.analysis_collaboration_repository import AnalysisCollaborationRepository
from app.repositories.dossier_analysis_repository import DossierAnalysisRepository


@contextmanager
def as_user(user_id: str, first: str = "", last: str = "") -> Iterator[None]:
    """Fait agir les requêtes en tant qu'un autre instructeur (le client de test est
    « dev-user » par défaut)."""
    app.dependency_overrides[get_current_user] = lambda: RequestContext(
        user_id=user_id,
        email=f"{user_id}@example.com",
        roles=[],
        is_admin=False,
        first_name=first,
        last_name=last,
        groups=["/dev-tests"],
    )
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def _run(client: TestClient, work: Callable[[AsyncSession], Awaitable[Any]]) -> Any:
    async def runner() -> Any:
        async with async_session_factory() as session:
            return await work(session)

    return client.portal.call(runner)


def _sql(client: TestClient, statement: str, **params: Any) -> None:
    async def work(session) -> None:
        await session.execute(text(statement), params)
        await session.commit()

    _run(client, work)


def _setup(client: TestClient, value: str = "Dupond") -> tuple[str, DossierAnalysis, AnalysisElement]:
    analyse_id = client.post("/api/analyses", json={"name": "Analyse collaboration", "description": "t"}).json()["id"]
    dossier_id = client.post("/api/dossiers", json={"name": "Dossier collaboration", "analyse_id": analyse_id}).json()[
        "id"
    ]

    async def work(session) -> tuple[DossierAnalysis, AnalysisElement]:
        repository = DossierAnalysisRepository(session)
        analysis = await repository.create_analysis(uuid.UUID(dossier_id))
        element = await repository.create_element(
            analysis,
            kind=AnalysisElementKind.ENTITY,
            value={"value": value},
            definition_name="nom",
            origin=ElementVersionOrigin.MODEL,
        )
        return analysis, element

    analysis, element = _run(client, work)
    return dossier_id, analysis, element


def _base(dossier_id: str, analysis_id: Any) -> str:
    return f"/api/dossiers/{dossier_id}/analyses-dossier/{analysis_id}"


def _lock(client: TestClient, dossier_id: str, analysis_id: Any, element_id: Any):
    return client.post(f"{_base(dossier_id, analysis_id)}/elements/{element_id}/lock")


def _unlock(client: TestClient, dossier_id: str, analysis_id: Any, element_id: Any):
    return client.delete(f"{_base(dossier_id, analysis_id)}/elements/{element_id}/lock")


def _edit(client: TestClient, dossier_id: str, analysis_id: Any, element_id: Any, value: str, **extra: Any):
    return client.post(
        f"{_base(dossier_id, analysis_id)}/elements/{element_id}/versions",
        json={"value": {"value": value}, "reason": "Correction", **extra},
    )


def _retained(client: TestClient, dossier_id: str, element_id: Any) -> dict[str, Any]:
    elements = client.get(f"/api/dossiers/{dossier_id}/analyse-dossier").json()["elements"]
    return next(e for e in elements if e["id"] == str(element_id))["retained_version"]


# --- Verrou ---


def test_taking_the_lock_returns_the_holder_and_an_expiry(client: TestClient) -> None:
    dossier_id, analysis, element = _setup(client)
    response = _lock(client, dossier_id, analysis.id, element.id)

    assert response.status_code == 200
    body = response.json()
    assert body["element_id"] == str(element.id)
    assert body["locked_by"] == "dev-user" and body["held_by_me"] is True
    assert body["locked_by_name"]
    assert body["locked_until"]
    # Le verrou expire seul : jamais d'élément bloqué indéfiniment.
    until = _run(client, lambda s: AnalysisCollaborationRepository(s).get_element(analysis.id, element.id)).locked_until
    seconds = (until - _now()).total_seconds()
    assert 0 < seconds <= collaboration.settings.ELEMENT_LOCK_TTL_SECONDS + 1


def _now():
    from datetime import UTC, datetime

    return datetime.now(UTC)


def test_another_instructor_cannot_take_a_held_lock_and_is_told_who_holds_it(client: TestClient) -> None:
    dossier_id, analysis, element = _setup(client)
    with as_user("marie", "Marie", "Durand"):
        assert _lock(client, dossier_id, analysis.id, element.id).status_code == 200

    response = _lock(client, dossier_id, analysis.id, element.id)  # dev-user

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert "Marie Durand" in detail
    assert "réessayez" in detail


def test_the_holder_renews_its_own_lock(client: TestClient) -> None:
    dossier_id, analysis, element = _setup(client)
    _lock(client, dossier_id, analysis.id, element.id)
    _sql(
        client,
        "UPDATE analysis_elements SET locked_until = now() + interval '5 seconds' WHERE id = :id",
        id=str(element.id),
    )

    again = _lock(client, dossier_id, analysis.id, element.id)

    assert again.status_code == 200
    until = _run(client, lambda s: AnalysisCollaborationRepository(s).get_element(analysis.id, element.id)).locked_until
    assert (until - _now()).total_seconds() > 30  # renouvelé : plus proche du TTL complet


def test_an_expired_lock_is_free_for_anyone(client: TestClient) -> None:
    dossier_id, analysis, element = _setup(client)
    with as_user("marie", "Marie", "Durand"):
        _lock(client, dossier_id, analysis.id, element.id)
    _sql(
        client,
        "UPDATE analysis_elements SET locked_until = now() - interval '1 second' WHERE id = :id",
        id=str(element.id),
    )

    taken = _lock(client, dossier_id, analysis.id, element.id)

    assert taken.status_code == 200 and taken.json()["locked_by"] == "dev-user"


def test_releasing_a_lock(client: TestClient) -> None:
    dossier_id, analysis, element = _setup(client)
    _lock(client, dossier_id, analysis.id, element.id)

    assert _unlock(client, dossier_id, analysis.id, element.id).status_code == 204

    with as_user("marie", "Marie", "Durand"):
        assert _lock(client, dossier_id, analysis.id, element.id).status_code == 200


def test_releasing_nothing_is_harmless_and_cannot_steal_someone_elses_lock(client: TestClient) -> None:
    dossier_id, analysis, element = _setup(client)
    assert _unlock(client, dossier_id, analysis.id, element.id).status_code == 204  # pas de verrou
    with as_user("marie", "Marie", "Durand"):
        _lock(client, dossier_id, analysis.id, element.id)

    assert _unlock(client, dossier_id, analysis.id, element.id).status_code == 409  # dev-user n'est pas le détenteur
    with as_user("paul", "Paul", "Martin"):
        assert (
            _lock(client, dossier_id, analysis.id, element.id).status_code == 409
        )  # le verrou de Marie tient toujours


def test_lock_errors(client: TestClient) -> None:
    dossier_id, analysis, element = _setup(client)
    assert _lock(client, dossier_id, analysis.id, uuid.uuid4()).status_code == 404
    other_dossier, other_analysis, _ = _setup(client)
    assert _lock(client, dossier_id, other_analysis.id, element.id).status_code == 404
    assert _lock(client, other_dossier, analysis.id, element.id).status_code == 404

    async def freeze(session) -> None:
        row = await session.get(DossierAnalysis, analysis.id)
        row.status = DossierAnalysisStatus.FIGEE
        await session.commit()

    _run(client, freeze)
    assert _lock(client, dossier_id, analysis.id, element.id).status_code == 409  # figée


# --- Une écriture est refusée tant qu'un autre détient le verrou ---


def test_a_write_is_refused_while_another_instructor_holds_the_lock(client: TestClient) -> None:
    dossier_id, analysis, element = _setup(client)
    with as_user("marie", "Marie", "Durand"):
        _lock(client, dossier_id, analysis.id, element.id)

    response = _edit(client, dossier_id, analysis.id, element.id, "Dupont")

    assert response.status_code == 409
    assert "Marie Durand" in response.json()["detail"]
    assert _retained(client, dossier_id, element.id)["value"] == {"value": "Dupond"}  # rien n'a été écrit


def test_the_holder_can_write_and_the_lock_is_released_afterwards(client: TestClient) -> None:
    dossier_id, analysis, element = _setup(client)
    _lock(client, dossier_id, analysis.id, element.id)

    assert _edit(client, dossier_id, analysis.id, element.id, "Dupont").status_code == 201

    assert _retained(client, dossier_id, element.id)["value"] == {"value": "Dupont"}
    # L'édition est finie : un autre peut prendre l'élément sans attendre l'expiration.
    with as_user("marie", "Marie", "Durand"):
        assert _lock(client, dossier_id, analysis.id, element.id).status_code == 200


def test_the_lock_is_not_required_to_write(client: TestClient) -> None:
    dossier_id, analysis, element = _setup(client)
    assert _edit(client, dossier_id, analysis.id, element.id, "Dupont").status_code == 201


def test_an_expired_lock_does_not_block_a_write(client: TestClient) -> None:
    dossier_id, analysis, element = _setup(client)
    with as_user("marie", "Marie", "Durand"):
        _lock(client, dossier_id, analysis.id, element.id)
    _sql(
        client,
        "UPDATE analysis_elements SET locked_until = now() - interval '1 second' WHERE id = :id",
        id=str(element.id),
    )
    assert _edit(client, dossier_id, analysis.id, element.id, "Dupont").status_code == 201


def test_a_restore_is_refused_while_another_instructor_holds_the_lock(client: TestClient) -> None:
    dossier_id, analysis, element = _setup(client)
    _edit(client, dossier_id, analysis.id, element.id, "Dupont")
    first = client.get(f"{_base(dossier_id, analysis.id)}/elements/{element.id}/versions").json()[0]
    with as_user("marie", "Marie", "Durand"):
        _lock(client, dossier_id, analysis.id, element.id)

    response = client.post(
        f"{_base(dossier_id, analysis.id)}/elements/{element.id}/restore", json={"version_id": first["id"]}
    )

    assert response.status_code == 409 and "Marie Durand" in response.json()["detail"]


def test_accepting_or_modifying_a_proposal_is_refused_while_another_holds_the_lock(client: TestClient) -> None:
    dossier_id, analysis, element = _setup(client)
    proposals = f"{_base(dossier_id, analysis.id)}/proposals"
    proposal = client.post(
        proposals, json={"element_id": str(element.id), "value": {"value": "Dupont"}, "reason": "Vérifié"}
    ).json()
    with as_user("marie", "Marie", "Durand"):
        _lock(client, dossier_id, analysis.id, element.id)

    accept = client.post(f"{proposals}/{proposal['id']}/accept")
    modify = client.post(f"{proposals}/{proposal['id']}/modify", json={"value": {"value": "Dupon"}})

    assert (accept.status_code, modify.status_code) == (409, 409)
    assert "Marie Durand" in accept.json()["detail"]
    # La proposition reste en attente et rien n'est appliqué.
    assert client.get(f"{proposals}/{proposal['id']}").json()["status"] == "pending"
    assert _retained(client, dossier_id, element.id)["value"] == {"value": "Dupond"}
    # Marie libère : la proposition peut être acceptée.
    with as_user("marie", "Marie", "Durand"):
        _unlock(client, dossier_id, analysis.id, element.id)
    assert client.post(f"{proposals}/{proposal['id']}/accept").status_code == 200


def test_rejecting_a_proposal_is_not_blocked_by_a_lock(client: TestClient) -> None:
    dossier_id, analysis, element = _setup(client)
    proposals = f"{_base(dossier_id, analysis.id)}/proposals"
    proposal = client.post(
        proposals, json={"element_id": str(element.id), "value": {"value": "Dupont"}, "reason": "Vérifié"}
    ).json()
    with as_user("marie", "Marie", "Durand"):
        _lock(client, dossier_id, analysis.id, element.id)
    assert client.post(f"{proposals}/{proposal['id']}/reject", json={}).status_code == 200  # ne modifie pas l'élément


def test_a_prediction_validation_is_refused_while_another_instructor_holds_the_lock(client: TestClient) -> None:
    analyse_id = client.post("/api/analyses", json={"name": "Analyse validation", "description": "t"}).json()["id"]
    dossier_id = client.post("/api/dossiers", json={"name": "Dossier validation", "analyse_id": analyse_id}).json()[
        "id"
    ]
    internal = {"X-App-Token": "dev-only-worker-token-not-for-prod"}
    document = client.post(
        f"/api/dossiers/{dossier_id}/documents", files=[("files", ("a.pdf", b"x", "application/pdf"))]
    ).json()["documents"][0]
    page = client.post(
        f"/api/internal/documents/{document['id']}/pages", json={"page_number": 1, "content": "t"}, headers=internal
    ).json()
    prediction = client.post(
        f"/api/internal/pages/{page['id']}/predictions",
        json={"kind": "entity", "name": "nom", "value": "Dupond"},
        headers=internal,
    ).json()
    url = (
        f"/api/dossiers/{dossier_id}/documents/{document['id']}/pages/{page['id']}"
        f"/predictions/{prediction['id']}/validations"
    )
    assert client.put(url, json={"status": "validé"}).status_code == 200  # crée l'élément
    element = client.get(f"/api/dossiers/{dossier_id}/analyse-dossier").json()["elements"][0]
    with as_user("marie", "Marie", "Durand"):
        _lock(client, dossier_id, element["analysis_id"], element["id"])

    response = client.put(url, json={"status": "corrigé", "corrected_value": "Dupont"})

    assert response.status_code == 409 and "Marie Durand" in response.json()["detail"]


# --- Contrôle de version ---


def test_a_stale_base_version_is_refused(client: TestClient) -> None:
    dossier_id, analysis, element = _setup(client)
    seen = _retained(client, dossier_id, element.id)["id"]
    assert _edit(client, dossier_id, analysis.id, element.id, "Dupont").status_code == 201  # un autre est passé avant

    stale = _edit(client, dossier_id, analysis.id, element.id, "Durand", base_version_id=seen)

    assert stale.status_code == 409
    assert "modifié" in stale.json()["detail"]
    assert _retained(client, dossier_id, element.id)["value"] == {"value": "Dupont"}


def test_the_current_base_version_is_accepted(client: TestClient) -> None:
    dossier_id, analysis, element = _setup(client)
    current = _retained(client, dossier_id, element.id)["id"]
    assert _edit(client, dossier_id, analysis.id, element.id, "Dupont", base_version_id=current).status_code == 201


# --- Écritures concurrentes ---


def test_two_simultaneous_edits_from_the_same_base_one_wins_the_other_is_refused(client: TestClient) -> None:
    dossier_id, analysis, element = _setup(client)
    base = _retained(client, dossier_id, element.id)["id"]

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(_edit, client, dossier_id, analysis.id, element.id, value, base_version_id=base)
            for value in ("Dupont", "Durand")
        ]
        codes = sorted(f.result().status_code for f in futures)

    assert codes == [201, 409]  # jamais deux écritures qui s'écrasent
    versions = client.get(f"{_base(dossier_id, analysis.id)}/elements/{element.id}/versions").json()
    assert [v["version_number"] for v in versions] == [1, 2]


def test_simultaneous_edits_without_a_base_are_serialised_never_duplicated(client: TestClient) -> None:
    dossier_id, analysis, element = _setup(client)

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(_edit, client, dossier_id, analysis.id, element.id, f"Valeur {i}") for i in range(4)]
        codes = [f.result().status_code for f in futures]

    assert codes == [201, 201, 201, 201]
    versions = client.get(f"{_base(dossier_id, analysis.id)}/elements/{element.id}/versions").json()
    # Une version par écriture, numérotées sans trou ni doublon (verrou de ligne).
    assert [v["version_number"] for v in versions] == [1, 2, 3, 4, 5]


def test_two_instructors_asking_for_the_lock_at_once_only_one_gets_it(client: TestClient) -> None:
    dossier_id, analysis, _ = _setup(client)

    async def contest(element_id: uuid.UUID) -> list[bool]:
        async def attempt(user: str) -> bool:
            async with async_session_factory() as session:
                taken = await AnalysisCollaborationRepository(session).acquire_lock(
                    analysis.id, element_id, user_id=user, name=user
                )
                return taken is not None

        return list(await asyncio.gather(*(attempt(f"user-{i}") for i in range(6))))

    async def create_elements(session) -> list[uuid.UUID]:
        repository = DossierAnalysisRepository(session)
        row = await session.get(DossierAnalysis, analysis.id)
        ids = []
        for i in range(5):
            element = await repository.create_element(
                row,
                kind=AnalysisElementKind.ENTITY,
                value={"value": f"v{i}"},
                definition_name=f"e{i}",
                origin=ElementVersionOrigin.MODEL,
            )
            ids.append(element.id)
        return ids

    element_ids = _run(client, create_elements)
    for element_id in element_ids:
        results = client.portal.call(lambda element_id=element_id: contest(element_id))
        assert results.count(True) == 1  # exactement un gagnant, à chaque fois


# --- Présence ---


def _presence(client: TestClient, dossier_id: str, analysis_id: Any, element_id: Any = None, mode: str = "viewing"):
    return client.put(
        f"{_base(dossier_id, analysis_id)}/presence",
        json={"element_id": str(element_id) if element_id else None, "mode": mode},
    )


def _snapshot(client: TestClient, dossier_id: str, analysis_id: Any) -> dict[str, Any]:
    return client.get(f"{_base(dossier_id, analysis_id)}/presence").json()


def test_presence_shows_who_is_on_which_element(client: TestClient) -> None:
    dossier_id, analysis, element = _setup(client)
    assert _snapshot(client, dossier_id, analysis.id) == {"presence": [], "locks": []}

    assert _presence(client, dossier_id, analysis.id, element.id, "editing").status_code == 204
    with as_user("marie", "Marie", "Durand"):
        _presence(client, dossier_id, analysis.id, None, "viewing")

    people = {p["user_id"]: p for p in _snapshot(client, dossier_id, analysis.id)["presence"]}
    assert set(people) == {"dev-user", "marie"}
    assert people["dev-user"]["element_id"] == str(element.id) and people["dev-user"]["mode"] == "editing"
    assert people["marie"]["element_id"] is None and people["marie"]["display_name"] == "Marie Durand"


def test_a_heartbeat_moves_the_presence_it_does_not_duplicate_it(client: TestClient) -> None:
    dossier_id, analysis, element = _setup(client)
    _presence(client, dossier_id, analysis.id, None, "viewing")
    _presence(client, dossier_id, analysis.id, element.id, "editing")
    [me] = _snapshot(client, dossier_id, analysis.id)["presence"]
    assert me["element_id"] == str(element.id) and me["mode"] == "editing"


def test_leaving_removes_the_presence(client: TestClient) -> None:
    dossier_id, analysis, element = _setup(client)
    _presence(client, dossier_id, analysis.id, element.id)
    assert client.delete(f"{_base(dossier_id, analysis.id)}/presence").status_code == 204
    assert _snapshot(client, dossier_id, analysis.id)["presence"] == []


def test_a_stale_presence_is_not_shown(client: TestClient) -> None:
    dossier_id, analysis, element = _setup(client)
    _presence(client, dossier_id, analysis.id, element.id)
    _sql(client, "UPDATE analysis_presence SET updated_at = now() - interval '5 minutes'")  # plus de battement de cœur
    assert _snapshot(client, dossier_id, analysis.id)["presence"] == []


def test_presence_errors(client: TestClient) -> None:
    dossier_id, analysis, _ = _setup(client)
    _, other_analysis, other_element = _setup(client)
    assert _presence(client, dossier_id, analysis.id, uuid.uuid4()).status_code == 404
    assert (
        _presence(client, dossier_id, analysis.id, other_element.id).status_code == 404
    )  # élément d'une autre analyse
    assert _presence(client, dossier_id, other_analysis.id).status_code == 404  # analyse d'un autre dossier
    bad = client.put(f"{_base(dossier_id, analysis.id)}/presence", json={"mode": "dancing"})
    assert bad.status_code == 422


def test_the_snapshot_lists_the_valid_locks_with_who_holds_them(client: TestClient) -> None:
    dossier_id, analysis, element = _setup(client)
    with as_user("marie", "Marie", "Durand"):
        _lock(client, dossier_id, analysis.id, element.id)

    [lock] = _snapshot(client, dossier_id, analysis.id)["locks"]
    assert lock["element_id"] == str(element.id)
    assert lock["locked_by"] == "marie" and lock["locked_by_name"] == "Marie Durand"
    assert lock["held_by_me"] is False  # vu par dev-user

    _sql(
        client,
        "UPDATE analysis_elements SET locked_until = now() - interval '1 second' WHERE id = :id",
        id=str(element.id),
    )
    assert _snapshot(client, dossier_id, analysis.id)["locks"] == []  # un verrou expiré n'est plus affiché


# --- Flux SSE ---


class _FakeRequest:
    """Requête dont le client se déconnecte au bout de ``checks`` vérifications (le
    TestClient ne sait pas lire un flux SSE infini : on exerce le générateur directement)."""

    def __init__(self, checks: int) -> None:
        self.remaining = checks

    async def is_disconnected(self) -> bool:
        self.remaining -= 1
        return self.remaining < 0


def _events(chunks: list[str]) -> list[dict[str, Any]]:
    return [json.loads(c.split("data:", 1)[1]) for c in chunks if c.startswith("event: live")]


def test_the_live_stream_sends_the_current_state_then_only_the_changes(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.routers.analysis_collaboration import _live_events

    monkeypatch.setattr(collaboration.settings, "LIVE_POLL_SECONDS", 0.01)
    dossier_id, analysis, element = _setup(client)

    async def watch() -> list[str]:
        chunks: list[str] = []
        stream = _live_events(_FakeRequest(checks=60), analysis.id, "dev-user")
        async for chunk in stream:
            chunks.append(chunk)
            if len(chunks) == 1:
                # Un instructeur arrive et verrouille un élément : le flux le voit.
                async with async_session_factory() as session:
                    repository = AnalysisCollaborationRepository(session)
                    await repository.upsert_presence(
                        analysis.id, user_id="marie", name="Marie Durand", element_id=element.id, mode="editing"
                    )
                    await repository.acquire_lock(analysis.id, element.id, user_id="marie", name="Marie Durand")
        return chunks

    events = _events(client.portal.call(watch))

    assert events[0] == {"presence": [], "locks": []}  # l'état à l'ouverture
    # Ensuite, seulement des changements : pas d'événement identique répété.
    assert len(events) >= 2 and all(a != b for a, b in zip(events, events[1:], strict=False))
    last = events[-1]
    assert [p["user_id"] for p in last["presence"]] == ["marie"]
    assert last["presence"][0]["mode"] == "editing" and last["presence"][0]["display_name"] == "Marie Durand"
    assert last["locks"][0]["locked_by"] == "marie" and last["locks"][0]["held_by_me"] is False  # vu par dev-user


def test_the_live_stream_stops_when_the_client_leaves(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.routers.analysis_collaboration import _live_events

    monkeypatch.setattr(collaboration.settings, "LIVE_POLL_SECONDS", 0.01)
    _, analysis, _ = _setup(client)

    async def watch() -> int:
        return len([chunk async for chunk in _live_events(_FakeRequest(checks=3), analysis.id, "dev-user")])

    assert client.portal.call(watch) == 1  # un état initial, puis fin : le générateur ne tourne pas dans le vide


def test_the_live_stream_sends_a_keepalive_when_nothing_changes(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.routers.analysis_collaboration import _live_events

    monkeypatch.setattr(collaboration.settings, "LIVE_POLL_SECONDS", 5.0)  # chaque tour compte 5 s d'inactivité
    _, analysis, _ = _setup(client)
    real_sleep = asyncio.sleep
    monkeypatch.setattr(asyncio, "sleep", lambda seconds: real_sleep(0))  # sans attendre réellement

    async def watch() -> list[str]:
        return [chunk async for chunk in _live_events(_FakeRequest(checks=6), analysis.id, "dev-user")]

    chunks = client.portal.call(watch)
    assert chunks[0].startswith("event: live")
    assert any(chunk.startswith(": keepalive") for chunk in chunks[1:])


def test_the_live_stream_requires_a_known_analysis(client: TestClient) -> None:
    dossier_id, _, _ = _setup(client)
    assert client.get(f"/api/dossiers/{dossier_id}/analyses-dossier/{uuid.uuid4()}/live").status_code == 404
