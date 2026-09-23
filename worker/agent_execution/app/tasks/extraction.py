"""Tâche d'extraction d'entités nommées.

Stratégie : regrouper les pages par batch (EXTRACTION_BATCH_SIZE, défaut 5)
pour optimiser le contexte et le coût. Pour chaque batch :
1. Envoyer le texte de toutes les pages au LLM avec les définitions
   d'entités et le prompt d'extraction.
2. Le LLM renvoie un structured output (ExtractionResult) listant les
   entités trouvées, avec pour chacune les numéros de pages où elle
   apparaît.
3. Déposer chaque entité comme une prédiction (kind=ENTITY) sur la
   première page où elle apparaît, en référençant toutes les pages
   concernées via page_ids.

Une entité qui s'étend sur plusieurs pages n'est déposée qu'une fois (sur
la première page), avec page_ids pointant vers toutes les pages où elle
apparaît - cohérent avec le modèle DocumentPrediction qui supporte les
entités multi-pages.
"""

import logging

from app import api_client, llm
from app.celery_app import celery_app
from app.config import settings
from app.tasks.classification import _STATUS_ECHEC, _STATUS_TERMINE, _find_step_id

logger = logging.getLogger(__name__)


def _collect_pages(dossier: dict) -> tuple[list[dict], dict[int, str]]:
    """Collecte toutes les pages de tous les documents. Renvoie la liste des
    pages (avec page_number, content, id) et un mapping page_number -> id."""
    all_pages: list[dict] = []
    page_id_by_number: dict[int, str] = {}
    for document in dossier["documents"]:
        for page in document["pages"]:
            page_number = page["page_number"]
            all_pages.append(
                {
                    "page_number": page_number,
                    "content": page.get("content") or "",
                    "id": page["id"],
                }
            )
            page_id_by_number[page_number] = page["id"]
    return all_pages, page_id_by_number


def _deposit_entity(
    client,
    entity_value,
    entity_def_by_name: dict,
    page_id_by_number: dict,
    batch_page_numbers: set,
) -> bool:
    """Dépose une entité extraite comme prédiction. Renvoie True si le dépôt
    a réussi, False si l'entité n'est pas dans les définitions."""
    entity_def = entity_def_by_name.get(entity_value.entity_name)
    if entity_def is None:
        logger.warning(
            "Entity '%s' not in definitions, skipping", entity_value.entity_name
        )
        return False

    entity_page_numbers = [
        pn for pn in entity_value.page_numbers if pn in batch_page_numbers
    ]
    if not entity_page_numbers:
        entity_page_numbers = [min(batch_page_numbers)]

    first_page_id = page_id_by_number[entity_page_numbers[0]]
    all_page_ids = [page_id_by_number[pn] for pn in entity_page_numbers]

    api_client.add_prediction(
        client,
        first_page_id,
        kind="entity",
        name=entity_value.entity_name,
        value=entity_value.value,
        confidence=entity_value.confidence,
        entity_definition_id=entity_def["id"],
        page_ids=all_page_ids,
    )
    logger.info(
        "Entity '%s' = '%s' (confidence=%.2f, pages=%s)",
        entity_value.entity_name,
        entity_value.value,
        entity_value.confidence,
        entity_page_numbers,
    )
    return True


def _process_batch(
    client,
    batch: list[dict],
    entity_defs: list[dict],
    entity_def_by_name: dict,
    extraction_prompt: str,
    page_id_by_number: dict,
) -> int:
    """Traite un batch de pages : extraction LLM + dépôt des entités.
    Renvoie le nombre d'entités déposées."""
    batch_page_numbers = {p["page_number"] for p in batch}

    result = llm.extract_entities_batch(
        pages=[
            {"page_number": p["page_number"], "content": p["content"]} for p in batch
        ],
        entity_definitions=entity_defs,
        extraction_prompt=extraction_prompt,
    )

    count = 0
    for entity_value in result.entities:
        if _deposit_entity(
            client,
            entity_value,
            entity_def_by_name,
            page_id_by_number,
            batch_page_numbers,
        ):
            count += 1
    return count


@celery_app.task(name="app.tasks.extract_dossier_entities", bind=True)
def extract_dossier_entities(self, dossier_id: str) -> None:
    with api_client.get_client() as client:
        dossier = api_client.get_dossier(client, dossier_id)
        analyse_id = dossier["analyse_id"]

        step_id = _find_step_id(dossier, "extraction")
        if step_id:
            api_client.add_execution_log(
                client, step_id, message="Extraction d'entités démarrée"
            )

        try:
            definitions = api_client.get_analyse_definitions(client, analyse_id)
            entity_defs = definitions["extraction"]["entities"]
            extraction_prompt = definitions["extraction"]["prompt"]

            if not entity_defs:
                logger.warning(
                    "No entity definitions for analyse %s, skipping extraction",
                    analyse_id,
                )
                if step_id:
                    api_client.complete_execution_step(
                        client,
                        step_id,
                        status=_STATUS_TERMINE,
                        output="Aucune entité définie",
                    )
                return

            entity_def_by_name = {entity["name"]: entity for entity in entity_defs}
            all_pages, page_id_by_number = _collect_pages(dossier)

            if not all_pages:
                if step_id:
                    api_client.complete_execution_step(
                        client,
                        step_id,
                        status=_STATUS_TERMINE,
                        output="Aucune page à traiter",
                    )
                return

            batch_size = settings.EXTRACTION_BATCH_SIZE
            total_entities = 0

            for i in range(0, len(all_pages), batch_size):
                batch = all_pages[i : i + batch_size]
                total_entities += _process_batch(
                    client,
                    batch,
                    entity_defs,
                    entity_def_by_name,
                    extraction_prompt,
                    page_id_by_number,
                )

            output = (
                f"{total_entities} entité(s) extraite(s) sur {len(all_pages)} page(s)"
            )
            if step_id:
                api_client.complete_execution_step(
                    client, step_id, status=_STATUS_TERMINE, output=output
                )
            logger.info("Extraction complete for dossier %s: %s", dossier_id, output)

        except Exception as error:
            logger.exception("Extraction failed for dossier %s", dossier_id)
            if step_id:
                api_client.add_execution_log(
                    client, step_id, level="error", message=str(error)
                )
                api_client.complete_execution_step(
                    client, step_id, status=_STATUS_ECHEC, output=str(error)
                )
            raise
