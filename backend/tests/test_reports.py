from fastapi.testclient import TestClient


def test_create_and_list_my_reports(client: TestClient) -> None:
    response = client.post(
        "/api/reports",
        data={"type": "bug", "title": "La sidebar clignote", "description": "Ça clignote au chargement."},
    )
    assert response.status_code == 201
    report = response.json()
    assert report["type"] == "bug"
    assert report["status"] == "new"
    assert report["has_screenshot"] is False
    assert report["admin_response"] is None

    listed = client.get("/api/reports").json()
    assert report["id"] in [r["id"] for r in listed]


def test_create_report_with_screenshot_is_relayed_through_the_backend(client: TestClient) -> None:
    response = client.post(
        "/api/reports",
        data={"type": "idea", "title": "Export PDF", "description": "Pouvoir exporter en PDF."},
        files={"screenshot": ("capture.png", b"fake-png-bytes", "image/png")},
    )
    assert response.status_code == 201
    report = response.json()
    assert report["has_screenshot"] is True

    screenshot = client.get(f"/api/reports/{report['id']}/screenshot")
    assert screenshot.status_code == 200
    assert screenshot.content == b"fake-png-bytes"
    assert screenshot.headers["content-type"] == "image/png"


def test_reports_list_is_private_to_its_user(client: TestClient) -> None:
    from app.core.security.factory import RequestContext, get_current_user
    from app.main import app

    client.post("/api/reports", data={"type": "question", "title": "Comment...", "description": "..."})

    def as_other_user() -> RequestContext:
        return RequestContext(user_id="other-user", email="other@example.com", roles=[], is_admin=False)

    app.dependency_overrides[get_current_user] = as_other_user
    try:
        assert client.get("/api/reports").json() == []
    finally:
        del app.dependency_overrides[get_current_user]


def test_admin_can_list_and_respond_to_reports(client: TestClient) -> None:
    created = client.post(
        "/api/reports", data={"type": "bug", "title": "Titre unique pour le test admin", "description": "Description"}
    ).json()

    listed = client.get("/api/admin/reports", params={"page_size": 100}).json()
    matching = [r for r in listed["items"] if r["id"] == created["id"]]
    assert len(matching) == 1
    assert matching[0]["user_display"]

    updated = client.patch(
        f"/api/admin/reports/{created['id']}",
        json={"status": "resolved", "admin_response": "Corrigé, merci !"},
    ).json()
    assert updated["status"] == "resolved"
    assert updated["admin_response"] == "Corrigé, merci !"
    assert updated["responded_by"] == "dev-user"


def test_admin_reports_route_is_forbidden_for_non_admin(client: TestClient) -> None:
    from app.core.security.factory import RequestContext, get_current_user
    from app.main import app

    def as_non_admin() -> RequestContext:
        return RequestContext(user_id="regular-user", email="regular@example.com", roles=[], is_admin=False)

    app.dependency_overrides[get_current_user] = as_non_admin
    try:
        response = client.get("/api/admin/reports")
        assert response.status_code == 403
    finally:
        del app.dependency_overrides[get_current_user]
