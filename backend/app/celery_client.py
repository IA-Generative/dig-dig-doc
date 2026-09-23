from celery import Celery

from app.config import RedisSettings

_redis_settings = RedisSettings()

# Producteur seulement : le backend ne définit ni n'exécute de tâches, il se
# contente d'en déposer sur la même file Redis que celle où
# worker/document_process écoute (voir son celery_app.py - même nom de
# tâche, aucune queue dédiée des deux côtés).
celery_client = Celery("dig-dig-doc-backend", broker=_redis_settings.REDIS_URL)


def dispatch_text_extraction(document_id: str) -> None:
    celery_client.send_task("app.tasks.extract_document_text", args=[document_id])
