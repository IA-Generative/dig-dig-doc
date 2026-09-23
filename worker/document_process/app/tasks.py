"""Tâche d'entrée du pipeline document_process : extraction de texte.

Télécharge le document depuis S3, en extrait le texte et une capture par
page (liteparse), puis écrit chaque page côté backend. Pas de NER/relations
ici (issue #4, prochaine étape) - juste le texte, comme convenu.
"""

import logging

from app import api_client
from app.celery_app import celery_app
from app.parsing import parse_file
from app.storage import storage

logger = logging.getLogger(__name__)


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

            api_client.add_page(
                client, document_id, page_number=page.page_num, content=page.text, screenshot_key=screenshot_key
            )

        logger.info("Extracted %d page(s) for document %s", len(result.pages), document_id)
