from unittest.mock import MagicMock

import fakeredis

from app.core.security.session import PendingAuth, SessionStore


def make_store() -> SessionStore:
    return SessionStore(
        redis_client=fakeredis.FakeRedis(decode_responses=True), keycloak_openid=MagicMock(), ttl_seconds=3600
    )


def test_pending_auth_round_trips_once() -> None:
    store = make_store()
    store.save_pending("state-1", PendingAuth(code_verifier="verifier", next_path="/dossiers"))

    pending = store.pop_pending("state-1")
    assert pending == PendingAuth(code_verifier="verifier", next_path="/dossiers")

    # A pending login attempt is one-time use: popping it again must fail,
    # otherwise a leaked/replayed `state` could complete a second login.
    assert store.pop_pending("state-1") is None


def test_create_and_get_session() -> None:
    store = make_store()
    identity = {"user_id": "u1", "email": "a@b.fr", "roles": [], "is_admin": False}
    token_response = {"access_token": "at", "refresh_token": "rt", "expires_in": 3600}

    session_id = store.create_session(identity, token_response)
    session = store.get_session(session_id)

    assert session is not None
    assert session.identity == identity
    assert session.access_token == "at"


def test_get_session_returns_none_once_deleted() -> None:
    store = make_store()
    session_id = store.create_session(
        {"user_id": "u1", "email": "", "roles": [], "is_admin": False},
        {"access_token": "at", "refresh_token": "rt", "expires_in": 3600},
    )

    store.delete_session(session_id)

    assert store.get_session(session_id) is None


def test_rate_limit_allows_then_blocks() -> None:
    store = make_store()
    assert store.check_rate_limit("k", limit=2, window_seconds=60) is True
    assert store.check_rate_limit("k", limit=2, window_seconds=60) is True
    assert store.check_rate_limit("k", limit=2, window_seconds=60) is False
