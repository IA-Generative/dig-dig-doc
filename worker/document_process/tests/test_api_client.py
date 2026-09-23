import httpx

from app.api_client import add_page, get_client, get_document
from app.config import WorkerSettings


def test_client_uses_configured_url_and_token() -> None:
    settings = WorkerSettings(BACKEND_INTERNAL_URL="http://backend:8000", INTERNAL_WORKER_TOKEN="test-token")
    client = httpx.Client(
        base_url=f"{settings.BACKEND_INTERNAL_URL}/api/internal",
        headers={"X-App-Token": settings.INTERNAL_WORKER_TOKEN},
    )
    try:
        assert str(client.base_url) == "http://backend:8000/api/internal/"
        assert client.headers["x-app-token"] == "test-token"
    finally:
        client.close()


def test_get_client_builds_a_working_client() -> None:
    client = get_client()
    try:
        assert client.base_url.path.endswith("/api/internal/")
        assert "x-app-token" in client.headers
    finally:
        client.close()


def test_get_document_and_add_page_call_the_expected_routes() -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, str(request.url)))
        if request.url.path.endswith("/pages"):
            return httpx.Response(201, json={"id": "page-1", "page_number": 1, "content": "hello"})
        return httpx.Response(200, json={"id": "doc-1", "s3_key": "dossiers/x/doc.pdf", "mimetype": "application/pdf"})

    client = httpx.Client(base_url="http://backend:8000/api/internal", transport=httpx.MockTransport(handler))
    try:
        document = get_document(client, "doc-1")
        assert document["s3_key"] == "dossiers/x/doc.pdf"

        page = add_page(client, "doc-1", page_number=1, content="hello")
        assert page["page_number"] == 1
    finally:
        client.close()

    assert calls == [
        ("GET", "http://backend:8000/api/internal/documents/doc-1"),
        ("POST", "http://backend:8000/api/internal/documents/doc-1/pages"),
    ]
