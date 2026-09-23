import httpx
from liteparse.types import ParsedPage, ParseResult, ScreenshotResult

from app import api_client
from app.tasks import extract_document_text


def test_extract_document_text_writes_pages_and_screenshots(monkeypatch) -> None:
    calls: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        if request.url.path.endswith("/documents/doc-1"):
            return httpx.Response(200, json={"id": "doc-1", "name": "cni.pdf", "s3_key": "dossiers/x/cni.pdf"})
        return httpx.Response(201, json={"id": "page-x"})

    monkeypatch.setattr(
        api_client,
        "get_client",
        lambda: httpx.Client(base_url="http://backend/api/internal", transport=httpx.MockTransport(handler)),
    )
    monkeypatch.setattr("app.tasks.storage.get_object", lambda key: b"fake-pdf-bytes")

    put_calls: list[tuple[str, bytes, str]] = []
    monkeypatch.setattr(
        "app.tasks.storage.put_object",
        lambda key, data, content_type="application/octet-stream": put_calls.append((key, data, content_type)),
    )

    parsed = ParseResult(
        pages=[
            ParsedPage(page_num=1, width=1000, height=1400, text="Page une"),
            ParsedPage(page_num=2, width=1000, height=1400, text="Page deux"),
        ],
        text="Page une\nPage deux",
        total_pages=2,
        screenshots=[ScreenshotResult(page_num=1, width=1000, height=1400, image_bytes=b"fake-png-bytes")],
    )
    monkeypatch.setattr("app.tasks.parse_file", lambda data: parsed)

    extract_document_text.run("doc-1")

    assert put_calls == [("screenshots/doc-1/page-1.png", b"fake-png-bytes", "image/png")]
    assert calls == [
        ("GET", "/api/internal/documents/doc-1"),
        ("POST", "/api/internal/documents/doc-1/pages"),
        ("POST", "/api/internal/documents/doc-1/pages"),
    ]
