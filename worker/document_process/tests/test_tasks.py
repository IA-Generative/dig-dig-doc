import json

import httpx
from liteparse.types import AnnotationRect, LayoutBlock, ParsedPage, ParseResult, ScreenshotResult

from app import api_client
from app.tasks import extract_document_text


def test_extract_document_text_writes_pages_bboxes_and_screenshots(monkeypatch) -> None:
    calls: list[tuple[str, str]] = []
    bbox_bodies: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        if request.url.path.endswith("/documents/doc-1"):
            return httpx.Response(200, json={"id": "doc-1", "name": "cni.pdf", "s3_key": "dossiers/x/cni.pdf"})
        if request.url.path.endswith("/pages"):
            return httpx.Response(201, json={"id": f"page-{len(calls)}"})
        if request.url.path.endswith("/bounding-boxes"):
            bbox_bodies.append(json.loads(request.content))
            return httpx.Response(201, json={"id": "bbox-1", **bbox_bodies[-1]})
        return httpx.Response(404)

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
            ParsedPage(
                page_num=1,
                width=1000,
                height=1400,
                text="Page une",
                blocks=[
                    LayoutBlock(
                        kind="paragraph", text="Page une", bbox=AnnotationRect(x=100, y=200, width=400, height=50)
                    )
                ],
            ),
            ParsedPage(page_num=2, width=1000, height=1400, text="Page deux", blocks=[]),
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
        ("POST", "/api/internal/pages/page-2/bounding-boxes"),
        ("POST", "/api/internal/documents/doc-1/pages"),
    ]
    assert bbox_bodies == [{"x_min": 0.1, "y_min": 0.14285714285714285, "x_max": 0.5, "y_max": 0.17857142857142858}]
