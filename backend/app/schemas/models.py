from pydantic import BaseModel


class LlmModel(BaseModel):
    id: str


class LlmModelsResponse(BaseModel):
    models: list[LlmModel]


class LlmModelsCacheCleared(BaseModel):
    """Réponse de DELETE /api/models/cache : confirme que le cache Redis
    des modèles chat a bien été invalidé."""

    cleared: bool
