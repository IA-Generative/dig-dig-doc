from celery import Celery

from app.config import settings

celery_app = Celery("document_process", broker=settings.celery_broker_url, backend=settings.celery_result_backend)

celery_app.conf.update(
    # Un document mal formé (PDF corrompu, OCR qui boucle) est tué plutôt
    # que de bloquer la queue - SIGKILL, pas une demande polie : le parsing
    # n'est pas interruptible proprement.
    task_time_limit=300,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
)

from app import tasks  # noqa: E402,F401
