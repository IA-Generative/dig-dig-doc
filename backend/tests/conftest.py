import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client() -> TestClient:
    # One event loop for the whole run, via the `with` context: app.db.engine
    # is a module-level singleton, and asyncpg connections from its pool
    # can't survive being reused across a fresh event loop per request (the
    # TestClient default outside a `with` block) - DB-backed tests would
    # fail with "another operation is in progress" / "different loop".
    with TestClient(app) as test_client:
        yield test_client
