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
    celery_client.send_task("app.tasks.classify_dossier", args=[dossier_id], queue="agent_execution")


def dispatch_entity_extraction(dossier_id: str) -> None:
    """Dépose la tâche d'extraction d'entités sur la file agent_execution.
    Le worker regroupe les pages par batch et extrait les entités via un
    LLM en structured output."""
    celery_client.send_task("app.tasks.extract_dossier_entities", args=[dossier_id], queue="agent_execution")


def dispatch_agent_execution(dossier_id: str) -> None:
    """Dépose la tâche d'exécution des agents sur la file agent_execution.
    Le worker attend que la classification et l'extraction soient terminées,
    puis exécute chaque agent via un graphe LangGraph avec des outils de
    recherche (BM25), lecture de pages, et consultation des prédictions."""
    celery_client.send_task("app.tasks.run_agents", args=[dossier_id], queue="agent_execution")


def dispatch_chat_response(conversation_id: str, dossier_id: str) -> None:
    """Dépose la tâche de réponse au chat sur la file agent_execution.
    Le worker charge l'historique de la conversation + les synthèses
    existantes (ExecutionStep.output), construit un graphe LangGraph avec
    les outils de recherche, et dépose la réponse de l'assistant (avec
    sources) via l'API interne. Les événements intermédiaires (tool_calls,
    tool_results) sont streamés via la table chat_events."""
    celery_client.send_task(
        "app.tasks.run_chat",
        args=[conversation_id, dossier_id],
        queue="agent_execution",
    )
