from pydantic import BaseModel


class ChatCompletionRequest(BaseModel):
    prompt: str
    # Identifiant de modèle tel que renvoyé par GET /models ; None = le
    # premier modèle chat-capable du hub est utilisé.
    model: str | None = None


class ChatCompletionResponse(BaseModel):
    content: str
