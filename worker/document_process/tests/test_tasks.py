import json

import httpx
from liteparse.types import AnnotationRect, LayoutBlock, ParsedPage, ParseResult, ScreenshotResult

from app import api_client
from app.tasks import extract_document_text


def test_extract_document_text_writes_pages_bboxes_screenshots_and_status(monkeypatch) -> None:
    calls: list[tuple[str, str]] = []
    bbox_bodies: list[dict] = []
    status_bodies: list[dict] = []
    page_ids = iter(["page-1", "page-2"])

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        if request.url.path.endswith("/extraction-status"):
            status_bodies.append(json.loads(request.content))
            return httpx.Response(200, json={"id": "doc-1", **status_bodies[-1]})
        if request.url.path.endswith("/file-hash"):
            return httpx.Response(200, json={"id": "doc-1", "file_hash": json.loads(request.content)["file_hash"]})
        if request.url.path.endswith("/documents/doc-1"):
            return httpx.Response(
                200,
                json={"id": "doc-1", "name": "cni.pdf", "s3_key": "dossiers/x/cni.pdf", "dossier_id": "dossier-xyz"},
            )
        if request.url.path.endswith("/pages"):
            return httpx.Response(201, json={"id": next(page_ids)})
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

    sent_tasks: list[tuple[str, tuple]] = []
    monkeypatch.setattr(
        "app.tasks.celery_app.send_task",
        lambda name, args=None, queue=None: sent_tasks.append((name, tuple(args or ()))),
    )

    extract_document_text.run("doc-1")

    assert put_calls == [("screenshots/doc-1/page-1.png", b"fake-png-bytes", "image/png")]
    assert calls == [
        ("PUT", "/api/internal/documents/doc-1/extraction-status"),
        ("GET", "/api/internal/documents/doc-1"),
        ("PUT", "/api/internal/documents/doc-1/file-hash"),
        ("POST", "/api/internal/documents/doc-1/pages"),
        ("POST", "/api/internal/pages/page-1/bounding-boxes"),
        ("POST", "/api/internal/documents/doc-1/pages"),
        ("PUT", "/api/internal/documents/doc-1/extraction-status"),
    ]
    assert bbox_bodies == [{"x_min": 0.1, "y_min": 0.14285714285714285, "x_max": 0.5, "y_max": 0.17857142857142858}]
    assert status_bodies == [{"status": "en_cours", "error": None}, {"status": "terminé", "error": None}]
    assert sent_tasks == [("app.tasks.run_document_summary", ("dossier-xyz", "doc-1"))]


def test_extract_document_text_reports_failure_status(monkeypatch) -> None:
    status_bodies: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/extraction-status"):
            status_bodies.append(json.loads(request.content))
            return httpx.Response(200, json={"id": "doc-1", **status_bodies[-1]})
        return httpx.Response(200, json={"id": "doc-1", "name": "cni.pdf", "s3_key": "dossiers/x/cni.pdf"})

    monkeypatch.setattr(
        api_client,
        "get_client",
        lambda: httpx.Client(base_url="http://backend/api/internal", transport=httpx.MockTransport(handler)),
    )

    def boom(key):
        raise ValueError("PDF corrompu")

    monkeypatch.setattr("app.tasks.storage.get_object", boom)

    try:
        extract_document_text.run("doc-1")
        raised = False
    except ValueError:
        raised = True

    assert raised
    assert status_bodies == [{"status": "en_cours", "error": None}, {"status": "échec", "error": "PDF corrompu"}]
