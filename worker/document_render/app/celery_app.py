from celery import Celery

from app.config import settings

celery_app = Celery("document_render", broker=settings.celery_broker_url, backend=settings.celery_result_backend)

celery_app.conf.update(
    # File propre à ce worker : les autres ne traitent jamais ces tâches (et inversement).
    task_default_queue="document_render",
    # Une conversion qui boucle est tuée plutôt que de bloquer la file.
    task_time_limit=300,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
)

from app import tasks  # noqa: E402,F401
