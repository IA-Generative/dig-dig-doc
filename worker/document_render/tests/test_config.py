"""Tests de la configuration du worker : d'où viennent le broker Celery et l'endpoint S3 (issue #148)."""

import pytest

from app.config import DEFAULT_REDIS_URL, DEFAULT_S3_ENDPOINT_URL, WorkerSettings


def settings(monkeypatch: pytest.MonkeyPatch, **env: str) -> WorkerSettings:
    for name in ("REDIS_URL", "CELERY_BROKER_URL", "CELERY_RESULT_BACKEND", "AWS_ENDPOINT_URL", "S3_ENDPOINT_URL"):
        monkeypatch.delenv(name, raising=False)
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    return WorkerSettings(_env_file=None)


def test_without_any_variable_the_worker_targets_local_services(monkeypatch: pytest.MonkeyPatch) -> None:
    config = settings(monkeypatch)
    assert config.celery_broker_url == config.celery_result_backend == DEFAULT_REDIS_URL
    assert config.s3_endpoint_url == DEFAULT_S3_ENDPOINT_URL


def test_the_redis_secret_of_kubernetes_serves_as_broker_and_results(monkeypatch: pytest.MonkeyPatch) -> None:
    config = settings(monkeypatch, REDIS_URL="redis://:motdepasse@digdigdoc-redis:6379/0")
    assert config.celery_broker_url == "redis://:motdepasse@digdigdoc-redis:6379/0"
    assert config.celery_result_backend == "redis://:motdepasse@digdigdoc-redis:6379/0"


def test_explicit_celery_urls_win_over_the_redis_url(monkeypatch: pytest.MonkeyPatch) -> None:
    config = settings(
        monkeypatch,
        REDIS_URL="redis://secret:6379/0",
        CELERY_BROKER_URL="redis://broker:6379/1",
        CELERY_RESULT_BACKEND="redis://results:6379/2",
    )
    assert config.celery_broker_url == "redis://broker:6379/1"
    assert config.celery_result_backend == "redis://results:6379/2"


def test_the_chart_endpoint_wins_and_a_bare_host_gets_a_scheme(monkeypatch: pytest.MonkeyPatch) -> None:
    # Le chart définit l'endpoint complet ; le secret peut donner un hôte sans schéma (boto3 le refuserait).
    config = settings(monkeypatch, AWS_ENDPOINT_URL="https://s3.fr-par.scw.cloud", S3_ENDPOINT_URL="s3.autre.example")
    assert config.s3_endpoint_url == "https://s3.fr-par.scw.cloud"
    assert settings(monkeypatch, S3_ENDPOINT_URL="s3.fr-par.scw.cloud").s3_endpoint_url == "https://s3.fr-par.scw.cloud"


def test_a_local_endpoint_keeps_its_scheme(monkeypatch: pytest.MonkeyPatch) -> None:
    assert settings(monkeypatch, S3_ENDPOINT_URL="http://rustfs:9000").s3_endpoint_url == "http://rustfs:9000"
