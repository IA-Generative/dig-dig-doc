from celery import Celery

from app.config import settings

celery_app = Celery(
    "agent_execution",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)
celery_app.conf.task_default_queue = "agent_execution"
