from __future__ import annotations

import httpx
import pytest

from millefeuille import (
    AuthenticationError,
    ConflictError,
    ConnectionFailedError,
    MilleFeuilleClient,
    MilleFeuilleError,
    NotFoundError,
    ServerError,
    ValidationError,
)
from millefeuille._http import normalize_base_url


def test_requires_credentials() -> None:
    with pytest.raises(ValueError):
        MilleFeuilleClient("https://api.test")


@pytest.mark.parametrize(
    ("url", "expected"),
    [("https://h", "https://h/api"), ("https://h/", "https://h/api"), ("https://h/api", "https://h/api")],
)
def test_normalize_base_url(url: str, expected: str) -> None:
    assert normalize_base_url(url) == expected


def test_auth_headers_and_cookie(make_client) -> None:
    client, seen = make_client(
        lambda r: httpx.Response(200, json={"models": []}), api_token="mille", bearer_token="b", session_cookie="s"
    )
    with client:
        client.models.list()
    request = seen[0]
    assert request.url == "https://api.test/api/models"
    assert request.headers["X-App-Token"] == "mille"
    assert request.headers["Authorization"] == "Bearer b"
    assert "millefeuille_session=s" in request.headers["cookie"]


@pytest.mark.parametrize(
    ("status", "exc"),
    [
        (401, AuthenticationError),
        (403, AuthenticationError),
        (404, NotFoundError),
        (409, ConflictError),
        (400, ValidationError),
        (422, ValidationError),
        (500, ServerError),
        (418, MilleFeuilleError),
    ],
)
def test_status_mapped_to_exception(make_client, status: int, exc: type[MilleFeuilleError]) -> None:
    client, _ = make_client(lambda r: httpx.Response(status, json={"detail": "boom"}), max_retries=0)
    with pytest.raises(exc) as info:
        client.models.list()
    assert info.value.status_code == status
    assert info.value.message == "boom"


def test_non_json_error_body(make_client) -> None:
    client, _ = make_client(lambda r: httpx.Response(404, text="nope"))
    with pytest.raises(NotFoundError, match="nope"):
        client.models.list()


def test_structured_detail(make_client) -> None:
    client, _ = make_client(lambda r: httpx.Response(422, json={"detail": [{"msg": "x"}]}))
    with pytest.raises(ValidationError, match="msg"):
        client.models.list()


def test_retry_on_5xx_for_get(make_client) -> None:
    responses = [httpx.Response(503), httpx.Response(502), httpx.Response(200, json={"models": [{"id": "m"}]})]
    client, seen = make_client(lambda r: responses.pop(0))
    assert [m.id for m in client.models.list()] == ["m"]
    assert len(seen) == 3


def test_retry_exhausted(make_client) -> None:
    client, seen = make_client(lambda r: httpx.Response(500), max_retries=2)
    with pytest.raises(ServerError):
        client.models.list()
    assert len(seen) == 3


def test_post_is_not_retried(make_client) -> None:
    client, seen = make_client(lambda r: httpx.Response(500))
    with pytest.raises(ServerError):
        client.analyses.create("n", "d")
    assert len(seen) == 1


def test_network_error_retried_then_raised(make_client) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    client, seen = make_client(handler, max_retries=1)
    with pytest.raises(ConnectionFailedError):
        client.models.list()
    assert len(seen) == 2
