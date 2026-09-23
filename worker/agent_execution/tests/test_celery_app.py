from app.celery_app import celery_app


def test_celery_app_configured() -> None:
    assert celery_app.main == "agent_execution"


def test_celery_app_has_agent_execution_queue() -> None:
    assert celery_app.conf.task_default_queue == "agent_execution"
