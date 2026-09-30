from __future__ import annotations

import json
import uuid

import httpx
import pytest
from conftest import analyse_json, run_json

from digdigdoc_ephemeral import (
    ConflictError,
    EphemeralAnalysisConfig,
    EphemeralClient,
    NotFoundError,
    TTLValidationError,
    ValidationError,
    WaitTimeoutError,
)


def test_requires_credentials() -> None:
    with pytest.raises(ValueError):
        EphemeralClient("https://api.test")


def test_context_manager_and_auth_header(make_client) -> None:
    aid = str(uuid.uuid4())
    client, seen = make_client(lambda r: httpx.Response(200, json=analyse_json(aid, persist=True)))
    with client:
        analyse = client.analyses.get(aid)
    assert analyse.persist is True
    assert seen[0].headers["X-App-Token"] == "ddd_tok"
    assert seen[0].url.path == f"/api/ephemeral/analyses/{aid}"


def test_analyses_create_sends_full_definition_then_gets(make_client) -> None:
    aid = str(uuid.uuid4())

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            body = json.loads(request.content)
            assert body["name"] == "Analyse"
            assert body["persist"] is True
            assert (
                body["labels"] == [{"name": "CNI", "definition": "Carte", "id": None}]
                or body["labels"][0]["name"] == "CNI"
            )
            assert body["entities"][0]["type"] == "texte"
            assert body["agents"][0]["prompt"] == "vérifie"
            return httpx.Response(201, json={"analyse_id": aid})
        return httpx.Response(200, json=analyse_json(aid, persist=True))

    client, seen = make_client(handler)
    analyse = client.analyses.create(
        "Analyse",
        persist=True,
        classification_prompt="c",
        labels=[{"name": "CNI", "definition": "Carte"}],
        extraction_prompt="e",
        entities=[{"name": "nom", "definition": "Nom", "type": "texte"}],
        agents=[{"name": "vérif", "prompt": "vérifie"}],
    )
    assert str(analyse.id) == aid
    assert [r.method for r in seen] == ["POST", "GET"]


def test_analyses_delete_conflict(make_client) -> None:
    client, _ = make_client(lambda r: httpx.Response(409, json={"detail": "runs liés"}))
    with pytest.raises(ConflictError, match="runs liés"):
        client.analyses.delete("x")


def test_runs_create_flux_b(make_client) -> None:
    rid = str(uuid.uuid4())
    aid = str(uuid.uuid4())

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            assert request.url.path == "/api/ephemeral/runs"
            assert request.url.params["ttl_hours"] == "48"
            assert f'name="analyse_id"\r\n\r\n{aid}'.encode() in request.content
            assert b'name="persist"\r\n\r\ntrue' in request.content
            assert b'filename="cni.pdf"' in request.content
            return httpx.Response(201, json={"run_id": rid})
        return httpx.Response(200, json=run_json(rid))

    client, _ = make_client(handler)
    run = client.runs.create(aid, [("cni.pdf", b"%PDF")], persist=True, ttl_hours=48)
    assert str(run.id) == rid and run.ttl_hours == 24


def test_runs_create_for_analyse_flux_a_without_ttl(make_client) -> None:
    rid = str(uuid.uuid4())

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            assert request.url.path == "/api/ephemeral/analyses/A1/runs"
            assert "ttl_hours" not in request.url.params
            assert b'name="persist"\r\n\r\nfalse' in request.content
            return httpx.Response(201, json={"run_id": rid})
        return httpx.Response(200, json=run_json(rid))

    client, _ = make_client(handler)
    client.runs.create_for_analyse("A1", [b"data"])


@pytest.mark.parametrize("ttl", [0, -1, 17521])
def test_ttl_validated_client_side(make_client, ttl: int) -> None:
    client, seen = make_client(lambda r: httpx.Response(500))
    with pytest.raises(TTLValidationError):
        client.runs.create("a", [b"x"], ttl_hours=ttl)
    with pytest.raises(ValueError):
        client.runs.create_for_analyse("a", [b"x"], ttl_hours=ttl)
    assert seen == []


def test_ttl_max_accepted(make_client) -> None:
    rid = str(uuid.uuid4())
    client, _ = make_client(
        lambda r: (
            httpx.Response(201, json={"run_id": rid}) if r.method == "POST" else httpx.Response(200, json=run_json(rid))
        )
    )
    client.runs.create("a", [b"x"], ttl_hours=17520)


def test_server_ttl_400_becomes_ttl_error(make_client) -> None:
    client, _ = make_client(
        lambda r: httpx.Response(400, json={"detail": "ttl_hours doit être compris entre 1 et 17520"})
    )
    with pytest.raises(TTLValidationError) as info:
        client.runs.create("a", [b"x"])
    assert info.value.status_code == 400


def test_other_400_stays_validation_error(make_client) -> None:
    client, _ = make_client(lambda r: httpx.Response(400, json={"detail": "autre"}))
    with pytest.raises(ValidationError) as info:
        client.runs.create("a", [b"x"])
    assert not isinstance(info.value, TTLValidationError)


def test_runs_stop_delete_not_found(make_client) -> None:
    rid = str(uuid.uuid4())

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "DELETE":
            return httpx.Response(404, json={"detail": "Run introuvable"})
        return httpx.Response(200, json=run_json(rid, status="arrêté"))

    client, _ = make_client(handler)
    assert client.runs.stop(rid).status.value == "arrêté"
    with pytest.raises(NotFoundError):
        client.runs.delete(rid)


def test_runs_wait(make_client, monkeypatch: pytest.MonkeyPatch) -> None:
    statuses = iter(["en_cours", "terminé"])
    client, _ = make_client(lambda r: httpx.Response(200, json=run_json(status=next(statuses))))
    monkeypatch.setattr("digdigdoc._polling.time.sleep", lambda s: None)
    assert client.runs.wait("r", poll_interval=0).status.is_terminal


def test_runs_wait_timeout(make_client) -> None:
    client, _ = make_client(lambda r: httpx.Response(200, json=run_json(status="en_cours")))
    with pytest.raises(WaitTimeoutError):
        client.runs.wait("r", timeout=0, poll_interval=1)


def _analyze_handler(aid: str, rid: str, log: list[tuple[str, str]], *, final: str = "terminé"):
    def handler(request: httpx.Request) -> httpx.Response:
        log.append((request.method, request.url.path))
        path = request.url.path
        if request.method == "POST" and path == "/api/ephemeral/analyses":
            return httpx.Response(201, json={"analyse_id": aid})
        if request.method == "POST":
            return httpx.Response(201, json={"run_id": rid})
        if request.method == "DELETE":
            return httpx.Response(204)
        if "analyses" in path:
            return httpx.Response(200, json=analyse_json(aid))
        return httpx.Response(200, json=run_json(rid, status=final))

    return handler


def test_analyze_one_liner(make_client) -> None:
    aid, rid = str(uuid.uuid4()), str(uuid.uuid4())
    log: list[tuple[str, str]] = []
    client, _ = make_client(_analyze_handler(aid, rid, log))
    result = client.analyze([b"x"], EphemeralAnalysisConfig(name="N"), ttl_hours=48, timeout=10, poll_interval=0)
    assert result.status.value == "terminé"
    assert not any(method == "DELETE" for method, _ in log)


def test_analyze_cleanup_deletes_run_then_analyse(make_client) -> None:
    aid, rid = str(uuid.uuid4()), str(uuid.uuid4())
    log: list[tuple[str, str]] = []
    client, _ = make_client(_analyze_handler(aid, rid, log))
    client.analyze([b"x"], EphemeralAnalysisConfig(name="N"), cleanup=True, poll_interval=0)
    assert [e for e in log if e[0] == "DELETE"] == [
        ("DELETE", f"/api/ephemeral/runs/{rid}"),
        ("DELETE", f"/api/ephemeral/analyses/{aid}"),
    ]


def test_analyze_with_existing_analyse_never_deletes_it(make_client) -> None:
    aid, rid = str(uuid.uuid4()), str(uuid.uuid4())
    log: list[tuple[str, str]] = []
    client, _ = make_client(_analyze_handler(aid, rid, log))
    client.analyze([b"x"], analyse_id=aid, cleanup=True, poll_interval=0)
    assert [e for e in log if e[0] == "DELETE"] == [("DELETE", f"/api/ephemeral/runs/{rid}")]


def test_analyze_needs_exactly_one_source(make_client) -> None:
    client, _ = make_client(lambda r: httpx.Response(500))
    with pytest.raises(ValueError):
        client.analyze([b"x"])
    with pytest.raises(ValueError):
        client.analyze([b"x"], EphemeralAnalysisConfig(name="N"), analyse_id="a")


def test_analyze_timeout_cleans_created_analyse(make_client) -> None:
    aid, rid = str(uuid.uuid4()), str(uuid.uuid4())
    log: list[tuple[str, str]] = []
    client, _ = make_client(_analyze_handler(aid, rid, log, final="en_cours"))
    with pytest.raises(WaitTimeoutError):
        client.analyze([b"x"], EphemeralAnalysisConfig(name="N"), timeout=0, poll_interval=1, cleanup=True)
    assert ("DELETE", f"/api/ephemeral/analyses/{aid}") in log


def test_analyze_cleanup_error_does_not_mask_original(make_client) -> None:
    aid = str(uuid.uuid4())

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/ephemeral/analyses" and request.method == "POST":
            return httpx.Response(201, json={"analyse_id": aid})
        if request.method == "GET":
            return httpx.Response(200, json=analyse_json(aid))
        if request.method == "DELETE":
            return httpx.Response(409, json={"detail": "x"})
        return httpx.Response(404, json={"detail": "Analyse introuvable"})

    client, _ = make_client(handler)
    with pytest.raises(NotFoundError):
        client.analyze([b"x"], EphemeralAnalysisConfig(name="N"), cleanup=True)


def test_config_validates_inputs() -> None:
    from pydantic import ValidationError as PydanticValidationError

    with pytest.raises(PydanticValidationError):
        EphemeralAnalysisConfig(name="  ")
    with pytest.raises(PydanticValidationError):
        EphemeralAnalysisConfig(name="n", agents=[{"name": "a", "prompt": ""}])  # type: ignore[list-item]
    with pytest.raises(PydanticValidationError):
        EphemeralAnalysisConfig(name="n", entities=[{"name": "e", "type": "couleur"}])  # type: ignore[list-item]
    with pytest.raises(PydanticValidationError):
        EphemeralAnalysisConfig(name="n", persit=True)  # type: ignore[call-arg]


def test_invalid_analysis_never_reaches_the_network(make_client) -> None:
    from pydantic import ValidationError as PydanticValidationError

    client, seen = make_client(lambda r: httpx.Response(500))
    with pytest.raises(PydanticValidationError):
        client.analyses.create("n", agents=[{"name": "a", "prompt": ""}])
    assert seen == []


def test_run_output_is_typed(make_client) -> None:
    from digdigdoc.models import DossierStatus

    client, _ = make_client(lambda r: httpx.Response(200, json=run_json(status="terminé")))
    run = client.runs.get("r")
    assert run.status is DossierStatus.TERMINE and run.ttl_hours == 24 and run.expires_at is None
