"""Tests for /api/me/tasks endpoints (issue #62)."""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import DatabaseSettings
from app.models.user_task import UserTask, UserTaskKind, UserTaskStatus
from app.schemas.user_task import UserTaskUpdateIn
from app.services.user_task_service import create_task, update_task


def _run_async(coro_factory):
    """Exécute une coroutine dans un thread séparé avec sa propre event loop
    et son propre engine SQLAlchemy.

    Le TestClient de Starlette occupe la loop principale du thread de test,
    et asyncpg refuse de partager une connexion entre deux loops. On crée
    donc un engine frais (et sa pool) dans chaque thread de seed.
    """

    import asyncio
    import threading

    result: dict = {}

    def _runner():
        loop = asyncio.new_event_loop()
        try:
            engine = create_async_engine(DatabaseSettings().DATABASE_URL)
            session_factory = async_sessionmaker(engine, expire_on_commit=False)
            result["value"] = loop.run_until_complete(coro_factory(session_factory))
            loop.run_until_complete(engine.dispose())
        except Exception as exc:  # noqa: BLE001
            result["error"] = exc
        finally:
            loop.close()

    t = threading.Thread(target=_runner)
    t.start()
    t.join()
    if "error" in result:
        raise result["error"]
    return result.get("value")


def _seed_task(**overrides) -> uuid.UUID:
    """Crée une tâche en DB de façon synchrone (depuis un test synchrone)."""

    async def _create(session_factory):
        async with session_factory() as db:
            defaults = {
                "user_id": "dev-user",
                "kind": UserTaskKind.TEXT_EXTRACTION,
                "celery_task_id": "celery-test",
            }
            defaults.update(overrides)
            task = await create_task(db, **defaults)
            return task.id

    return _run_async(_create)


def _cleanup_task(*task_ids: uuid.UUID) -> None:
    """Supprime les tâches de test."""

    async def _delete(session_factory):
        from sqlalchemy import delete

        async with session_factory() as db:
            await db.execute(delete(UserTask).where(UserTask.id.in_(task_ids)))
            await db.commit()

    _run_async(_delete)


def _mark_running(task_id: uuid.UUID) -> None:
    """Marque une tâche comme RUNNING (via le service)."""

    async def _update(session_factory):
        async with session_factory() as db:
            await update_task(db, task_id, UserTaskUpdateIn(status=UserTaskStatus.RUNNING))

    _run_async(_update)


# ── /api/me/tasks ──────────────────────────────────────────────────────────


def _purge_user_tasks(user_id: str = "dev-user") -> None:
    """Supprime toutes les tâches d'un utilisateur (isolation des tests)."""

    async def _purge(session_factory):
        from sqlalchemy import delete

        async with session_factory() as db:
            await db.execute(delete(UserTask).where(UserTask.user_id == user_id))
            await db.commit()

    _run_async(_purge)


def setup_function(_function):
    """Nettoie les tâches de dev-user avant chaque test."""
    _purge_user_tasks()


def test_list_tasks_empty(client: TestClient) -> None:
    """L'utilisateur dev-user n'a aucune tâche au départ."""
    response = client.get("/api/me/tasks")
    assert response.status_code == 200
    assert response.json() == []


def test_list_tasks_returns_created_task(client: TestClient) -> None:
    """Crée une tâche via le service, puis vérifie qu'elle apparaît."""
    task_id = _seed_task(kind=UserTaskKind.TEXT_EXTRACTION, celery_task_id="celery-123")
    try:
        response = client.get("/api/me/tasks")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        found = next(t for t in data if t["id"] == str(task_id))
        assert found["kind"] == "text_extraction"
        assert found["status"] == "pending"
        assert found["celery_task_id"] == "celery-123"
        assert found["label"] == "Extraction de texte"
    finally:
        _cleanup_task(task_id)


def test_get_task_by_id(client: TestClient) -> None:
    """GET /api/me/tasks/{id} retourne une tâche spécifique."""
    task_id = _seed_task(kind=UserTaskKind.CLASSIFICATION, celery_task_id="celery-456")
    try:
        response = client.get(f"/api/me/tasks/{task_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(task_id)
        assert data["kind"] == "classification"
        assert data["label"] == "Classification documentaire"
    finally:
        _cleanup_task(task_id)


def test_get_task_404_for_unknown_id(client: TestClient) -> None:
    """GET /api/me/tasks/{id} retourne 404 pour un ID inexistant."""
    response = client.get("/api/me/tasks/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_list_tasks_filter_by_status(client: TestClient) -> None:
    """Filtrage par statut via query param ?status=."""
    t1 = _seed_task(kind=UserTaskKind.AGENT_EXECUTION)
    t2 = _seed_task(kind=UserTaskKind.CHAT_RESPONSE)
    _mark_running(t2)
    try:
        # Tâches pending seulement
        response = client.get("/api/me/tasks?status=pending")
        assert response.status_code == 200
        data = response.json()
        ids = [t["id"] for t in data]
        assert str(t1) in ids
        assert str(t2) not in ids

        # Tâches running seulement
        response = client.get("/api/me/tasks?status=running")
        assert response.status_code == 200
        data = response.json()
        ids = [t["id"] for t in data]
        assert str(t2) in ids
        assert str(t1) not in ids
    finally:
        _cleanup_task(t1, t2)


# ── /api/internal/user-tasks/{id} (callback worker) ────────────────────────


def test_internal_update_task_status(client: TestClient) -> None:
    """Le worker met à jour le statut d'une tâche via l'API interne."""
    task_id = _seed_task(kind=UserTaskKind.ENTITY_EXTRACTION, celery_task_id="celery-789")
    try:
        # Le worker marque la tâche comme RUNNING
        response = client.put(
            f"/api/internal/user-tasks/{task_id}",
            json={"status": "running"},
            headers={"X-App-Token": "dev-only-worker-token-not-for-prod"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"

        # Puis SUCCESS
        response = client.put(
            f"/api/internal/user-tasks/{task_id}",
            json={"status": "success"},
            headers={"X-App-Token": "dev-only-worker-token-not-for-prod"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        # Vérifie via l'API utilisateur
        response = client.get(f"/api/me/tasks/{task_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "success"
    finally:
        _cleanup_task(task_id)


def test_internal_update_task_404(client: TestClient) -> None:
    """404 si la tâche n'existe pas."""
    response = client.put(
        "/api/internal/user-tasks/00000000-0000-0000-0000-000000000000",
        json={"status": "running"},
        headers={"X-App-Token": "dev-only-worker-token-not-for-prod"},
    )
    assert response.status_code == 404
