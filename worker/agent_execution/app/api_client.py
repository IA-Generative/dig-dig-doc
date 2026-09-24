import httpx

from app.config import settings


def get_client() -> httpx.Client:
    """Client HTTP authentifié vers le BFF, pour tous les appels à
    /api/internal/* (logs d'exécution, prédictions déposées, définitions
    de l'analyse...). Le jeton (voir app.core.security.internal.verify_app_token
    côté backend) est soit le secret de bootstrap fixe (dev local, docker-
    compose), soit le jeton en clair d'un AppToken créé via
    POST /api/app-tokens (prod, révocable indépendamment) - les deux
    marchent avec la même variable d'environnement, sans changement de
    code ici."""
    return httpx.Client(
        base_url=f"{settings.BACKEND_INTERNAL_URL}/api/internal",
        headers={"X-App-Token": settings.INTERNAL_WORKER_TOKEN},
        timeout=60.0,
    )


# --- Execution steps ---


def add_execution_log(client: httpx.Client, step_id: str, *, level: str = "info", message: str) -> dict:
    response = client.post(f"/execution-steps/{step_id}/logs", json={"level": level, "message": message})
    response.raise_for_status()
    return response.json()


def complete_execution_step(client: httpx.Client, step_id: str, *, status: str, output: str | None = None) -> dict:
    response = client.post(
        f"/execution-steps/{step_id}/complete",
        json={"status": status, "output": output},
    )
    response.raise_for_status()
    return response.json()


# --- Dossier & analyse definitions ---


def get_dossier(client: httpx.Client, dossier_id: str) -> dict:
    """Récupère le dossier avec ses documents, pages, et étapes d'exécution.
    Nécessite GET /internal/dossiers/{dossier_id} côté backend."""
    response = client.get(f"/dossiers/{dossier_id}")
    response.raise_for_status()
    return response.json()


def get_analyse_definitions(client: httpx.Client, analyse_id: str) -> dict:
    """Récupère les définitions de labels et d'entités de l'analyse, ainsi
    que les prompts de classification et d'extraction. Nécessite
    GET /internal/analyses/{analyse_id} côté backend."""
    response = client.get(f"/analyses/{analyse_id}")
    response.raise_for_status()
    return response.json()


# --- Predictions ---


def add_prediction(
    client: httpx.Client,
    page_id: str,
    *,
    kind: str,
    name: str,
    value: str,
    confidence: float | None = None,
    label_definition_id: str | None = None,
    entity_definition_id: str | None = None,
    page_ids: list[str] | None = None,
    bounding_box_ids: list[str] | None = None,
) -> dict:
    response = client.post(
        f"/pages/{page_id}/predictions",
        json={
            "kind": kind,
            "name": name,
            "value": value,
            "confidence": confidence,
            "label_definition_id": label_definition_id,
            "entity_definition_id": entity_definition_id,
            "page_ids": page_ids or [],
            "bounding_box_ids": bounding_box_ids or [],
        },
    )
    response.raise_for_status()
    return response.json()


# --- Conversations & chat events ---


def get_conversation(client: httpx.Client, conversation_id: str) -> dict:
    """Récupère la conversation complète (historique des messages + modèle
    LLM préféré) pour construire le contexte du graphe LangGraph de chat."""
    response = client.get(f"/conversations/{conversation_id}")
    response.raise_for_status()
    return response.json()


def add_chat_event(
    client: httpx.Client,
    conversation_id: str,
    *,
    kind: str,
    data: dict,
) -> dict:
    """Dépose un événement de chat (tool_call, tool_result, thinking, done,
    error). Le frontend consomme ces événements via SSE pour streamer la
    progression de l'exécution en temps réel."""
    response = client.post(
        f"/conversations/{conversation_id}/chat-events",
        json={"kind": kind, "data": data},
    )
    response.raise_for_status()
    return response.json()


def deposit_assistant_message(
    client: httpx.Client,
    conversation_id: str,
    *,
    content: str,
    sources: list[dict] | None = None,
) -> dict:
    """Dépose le message assistant final (avec sources) via l'API interne.
    Les sources référencent les documents/pages utilisés par l'agent pour
    construire sa réponse."""
    response = client.post(
        f"/conversations/{conversation_id}/messages",
        json={"content": content, "sources": sources or []},
    )
    response.raise_for_status()
    return response.json()
