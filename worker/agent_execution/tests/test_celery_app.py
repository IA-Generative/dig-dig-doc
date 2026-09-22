from app.celery_app import celery_app


def test_celery_app_configured() -> None:
    assert celery_app.main == "agent_execution"
