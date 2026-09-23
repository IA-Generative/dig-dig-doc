from celery import Celery

from app.config import RedisSettings

_redis_settings = RedisSettings()

# Producteur seulement : le backend ne définit ni n'exécute de tâches, il se
# contente d'en déposer sur la même file Redis que celle où
# worker/document_process et worker/agent_execution écoutent (voir leurs
# celery_app.py - même nom de tâche, aucune queue dédiée des deux côtés).
celery_client = Celery("dig-dig-doc-backend", broker=_redis_settings.REDIS_URL)


def dispatch_text_extraction(document_id: str) -> None:
    celery_client.send_task("app.tasks.extract_document_text", args=[document_id])


def dispatch_classification(dossier_id: str) -> None:
    """Dépose la tâche de classification documentaire sur la file
    agent_execution. Le worker télécharge les captures de pages depuis S3,
    les décrit via un VLM, puis classifie chaque page via un LLM en
    structured output."""
    celery_client.send_task(
        "app.tasks.classify_dossier", args=[dossier_id], queue="agent_execution"
    )


def dispatch_entity_extraction(dossier_id: str) -> None:
    """Dépose la tâche d'extraction d'entités sur la file agent_execution.
    Le worker regroupe les pages par batch et extrait les entités via un
    LLM en structured output."""
    celery_client.send_task(
        "app.tasks.extract_dossier_entities", args=[dossier_id], queue="agent_execution"
    )
