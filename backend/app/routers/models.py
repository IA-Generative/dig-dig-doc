import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from openai import AsyncOpenAI

from app.config import LlmSettings
from app.connectors import redis_connector
from app.core.security.factory import RequestContext, get_current_user
from app.schemas.models import LlmModel, LlmModelsResponse

router = APIRouter(prefix="/models", tags=["Models"])

_CHAT_MODELS_CACHE_KEY = "llm:chat_models"

# Module attributes (not closed over) so tests can swap them out with
# monkeypatch.setattr without a live LLM hub or Redis.
_llm_settings = LlmSettings()
_openai_client = (
    AsyncOpenAI(api_key=_llm_settings.OPENAI_API_KEY, base_url=_llm_settings.OPENAI_API_BASE_URL)
    if _llm_settings.is_configured
    else None
)


async def _supports_chat(model_id: str) -> bool:
    """The hub's /models endpoint lists everything it serves (embeddings, TTS,
    vision-only, ...), not just chat models - the only reliable way to tell
    them apart is to actually try a chat completion."""
    try:
        await _openai_client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1,
        )
        return True
    except Exception:
        return False


async def _discover_models(probe: Callable[[str], Awaitable[bool]]) -> list[str]:
    available = await _openai_client.models.list()
    candidate_ids = [model.id for model in available.data]
    supported = await asyncio.gather(*(probe(model_id) for model_id in candidate_ids))
    return sorted(model_id for model_id, ok in zip(candidate_ids, supported, strict=True) if ok)


@router.get("", summary="List the LLM hub's models that support chat completions", response_model=LlmModelsResponse)
async def list_models(_: Annotated[RequestContext, Depends(get_current_user)]) -> LlmModelsResponse:
    if _openai_client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="LLM hub is not configured")

    cached = redis_connector.client.get(_CHAT_MODELS_CACHE_KEY)
    if cached is not None:
        model_ids = json.loads(cached)
    else:
        model_ids = await _discover_models(_supports_chat)
        redis_connector.client.set(
            _CHAT_MODELS_CACHE_KEY, json.dumps(model_ids), ex=_llm_settings.CHAT_MODELS_CACHE_TTL_SECONDS
        )

    return LlmModelsResponse(models=[LlmModel(id=model_id) for model_id in model_ids])
