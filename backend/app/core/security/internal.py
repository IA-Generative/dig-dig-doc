import hmac
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import SharingSettings
from app.db import get_db
from app.repositories.app_token_repository import AppTokenRepository

_settings = SharingSettings()


async def verify_app_token(db: Annotated[AsyncSession, Depends(get_db)], x_app_token: Annotated[str, Header()]) -> None:
    """Auth des routes de callback (/api/internal/*) : les applications
    externes (workers Celery, scripts...) ne sont pas des clients Keycloak,
    donc pas de session/bearer utilisateur. Deux façons d'obtenir un jeton
    valide :
    - INTERNAL_WORKER_TOKEN, un secret fixe de bootstrap (docker-compose,
      dev local) - pratique pour démarrer sans configurer quoi que ce soit ;
    - un AppToken créé via POST /api/app-tokens (voir ce routeur),
      révocable indépendamment et nommé par application - à préférer en
      dehors du dev local.
    """
    if hmac.compare_digest(x_app_token, _settings.INTERNAL_WORKER_TOKEN):
        return
    app_token = await AppTokenRepository(db).verify(x_app_token)
    if app_token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Jeton invalide")
