"""Tâche d'entrée du pipeline document_process : extraction de texte.

Télécharge le document depuis S3, en extrait le texte, les bbox des blocs
de mise en page et une capture par page (liteparse), puis écrit chaque page
côté backend. Pas de NER/relations ici (issue #4, prochaine étape) - juste
le texte et sa localisation, comme convenu.
"""

import logging

from liteparse.types import AnnotationRect

from app import api_client
from app.celery_app import celery_app
from app.parsing import parse_file
from app.storage import storage

logger = logging.getLogger(__name__)


def _normalize(bbox: AnnotationRect, page_width: float, page_height: float) -> tuple[float, float, float, float] | None:
    """Pixels -> 0-1 (origine en haut à gauche), et bornée à la page : liteparse
    peut renvoyer une bbox qui déborde légèrement (ex: interligne)."""
    if not page_width or not page_height:
        return None
    x_min = max(0.0, min(1.0, bbox.x / page_width))
    y_min = max(0.0, min(1.0, bbox.y / page_height))
    x_max = max(0.0, min(1.0, (bbox.x + bbox.width) / page_width))
    y_max = max(0.0, min(1.0, (bbox.y + bbox.height) / page_height))
    return x_min, y_min, x_max, y_max


@celery_app.task(name="app.tasks.extract_document_text", bind=True)
def extract_document_text(self, document_id: str) -> None:
    with api_client.get_client() as client:
        document = api_client.get_document(client, document_id)
        logger.info("Extracting text for document %s (%s)", document_id, document["name"])

        data = storage.get_object(document["s3_key"])
        result = parse_file(data)
        screenshots_by_page = {screenshot.page_num: screenshot for screenshot in result.screenshots}

        for page in result.pages:
            screenshot_key: str | None = None
            screenshot = screenshots_by_page.get(page.page_num)
            if screenshot is not None:
                screenshot_key = f"screenshots/{document_id}/page-{page.page_num}.png"
                storage.put_object(screenshot_key, screenshot.image_bytes, content_type="image/png")

            created_page = api_client.add_page(
                client, document_id, page_number=page.page_num, content=page.text, screenshot_key=screenshot_key
            )

            bbox_count = 0
            for block in page.blocks or []:
                if not block.text or block.bbox is None:
                    continue
                normalized = _normalize(block.bbox, page.width, page.height)
                if normalized is None:
                    continue
                x_min, y_min, x_max, y_max = normalized
                api_client.add_bounding_box(
                    client, created_page["id"], x_min=x_min, y_min=y_min, x_max=x_max, y_max=y_max
                )
                bbox_count += 1

            logger.info("Page %d: %d bbox(es)", page.page_num, bbox_count)

        logger.info("Extracted %d page(s) for document %s", len(result.pages), document_id)
