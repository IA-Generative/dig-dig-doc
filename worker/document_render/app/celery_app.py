from celery import Celery

from app.config import settings

celery_app = Celery("document_render", broker=settings.CELERY_BROKER_URL, backend=settings.CELERY_RESULT_BACKEND)

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
