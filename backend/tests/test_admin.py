"""Tests for /api/admin/stats and /api/admin/tasks endpoints."""

from fastapi.testclient import TestClient


# ── /api/admin/stats ──────────────────────────────────────────────────────


def test_admin_stats_returns_counts(client: TestClient) -> None:
    response = client.get("/api/admin/stats")
    assert response.status_code == 200
    data = response.json()
    assert "analyses_count" in data
    assert "dossiers_count" in data
    assert "conversations_count" in data
    assert "messages_count" in data
    assert "agent_conversations_count" in data
    assert "agent_messages_count" in data
    assert "reports_count" in data
    assert "users_count" in data
    assert isinstance(data["dossiers_by_status"], dict)
    assert isinstance(data["daily_creations"], list)
    assert isinstance(data["top_models"], list)


def test_admin_stats_includes_created_report(client: TestClient) -> None:
    client.post(
        "/api/reports",
        data={"type": "bug", "title": "Stat test", "description": "..."},
    )
    data = client.get("/api/admin/stats").json()
    assert data["reports_count"] >= 1


def test_admin_stats_is_forbidden_for_non_admin(client: TestClient) -> None:
    from app.core.security.factory import RequestContext, get_current_user
    from app.main import app

    def as_non_admin() -> RequestContext:
        return RequestContext(
            user_id="regular-user",
            email="regular@example.com",
            roles=[],
            is_admin=False,
        )

    app.dependency_overrides[get_current_user] = as_non_admin
    try:
        response = client.get("/api/admin/stats")
        assert response.status_code == 403
    finally:
        del app.dependency_overrides[get_current_user]


# ── /api/admin/tasks ──────────────────────────────────────────────────────


def test_admin_tasks_returns_structure(client: TestClient) -> None:
    response = client.get("/api/admin/tasks")
    assert response.status_code == 200
    data = response.json()
    assert "workers" in data
    assert "registered" in data
    assert "active" in data
    assert "reserved" in data
    assert "scheduled" in data
    assert isinstance(data["workers"], list)
    assert isinstance(data["registered"], list)
    assert isinstance(data["active"], list)
    assert isinstance(data["reserved"], list)
    assert isinstance(data["scheduled"], list)


def test_admin_tasks_is_forbidden_for_non_admin(client: TestClient) -> None:
    from app.core.security.factory import RequestContext, get_current_user
    from app.main import app

    def as_non_admin() -> RequestContext:
        return RequestContext(
            user_id="regular-user",
            email="regular@example.com",
            roles=[],
            is_admin=False,
        )

    app.dependency_overrides[get_current_user] = as_non_admin
    try:
        response = client.get("/api/admin/tasks")
        assert response.status_code == 403
    finally:
        del app.dependency_overrides[get_current_user]
