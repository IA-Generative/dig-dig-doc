from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_login_redirects_to_keycloak() -> None:
    response = client.get("/api/auth/login", follow_redirects=False)
    assert response.status_code == 307
    location = response.headers["location"]
    assert "/protocol/openid-connect/auth" in location
    assert "client_id=dig-dig-doc-backend" in location
    assert "code_challenge=" in location


def test_login_rejects_unsafe_redirect() -> None:
    response = client.get("/api/auth/login?redirect=//evil.example.com", follow_redirects=False)
    location = response.headers["location"]
    # The unsafe redirect target never reaches Keycloak's query string; the
    # actual fallback ("/") is only visible after /callback, so here we just
    # assert the attacker-controlled host isn't smuggled through.
    assert "evil.example.com" not in location


def test_me_returns_dev_identity_when_verification_is_bypassed() -> None:
    # tests/.env.testing sets VERIFY_TOKEN_MODEL=full-access, so /me never
    # needs a real Keycloak or session cookie here.
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == "dev-user"
    assert body["is_admin"] is True
