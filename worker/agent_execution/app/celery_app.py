from celery import Celery

from app.config import settings

# `include` : les modules qui définissent des @celery_app.task ne sont
# jamais importés autrement (`celery -A app.celery_app worker` n'importe
# que ce module, pas ses voisins) - sans ce paramètre, le worker démarre
# avec un registre de tâches vide et rejette tout message reçu comme
# "unregistered task" (bug préexistant, découvert en travaillant sur
# app.tasks.run_helper_chat - voir docs/mcp-helper-agent-plan.md, Phase 7).
celery_app = Celery(
    "agent_execution",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.chat",
        "app.tasks.classification",
        "app.tasks.extraction",
        "app.tasks.agent",
        "app.tasks.helper_chat",
        "app.tasks.summary",
        "app.tasks.suggestion",
    ],
)
celery_app.conf.task_default_queue = "agent_execution"
