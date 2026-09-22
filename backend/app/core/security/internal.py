import hmac

from fastapi import Header, HTTPException, status

from app.config import SharingSettings

_settings = SharingSettings()


def verify_worker_token(x_worker_token: str = Header(...)) -> None:
    """Auth des routes de callback (/api/internal/*) : les workers Celery ne
    sont pas des clients Keycloak, donc pas de session/bearer utilisateur -
    juste un jeton partagé, comme MEILI_API_KEY pour meilisearch."""
    if not hmac.compare_digest(x_worker_token, _settings.INTERNAL_WORKER_TOKEN):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Jeton worker invalide")
