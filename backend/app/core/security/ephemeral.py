from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.factory import get_current_user
from app.db import get_db
from app.repositories.app_token_repository import AppTokenRepository


@dataclass
class EphemeralIdentity:
    """Identité de l'appelant d'un endpoint /api/ephemeral/* - stockée comme
    `created_by` sur les ressources éphémères, pour le scoping de visibilité
    (voir docs/ephemeral-api.md, section Authentification)."""

    id: str
    is_app_token: bool


async def get_ephemeral_identity(request: Request, db: Annotated[AsyncSession, Depends(get_db)]) -> EphemeralIdentity:
    """Les endpoints éphémères acceptent un jeton API (compte de service,
    header X-App-Token, même mécanisme que /api/internal/*) ou une session
    Keycloak standard - contrairement à /api/internal/*, pas de bypass par
    INTERNAL_WORKER_TOKEN : ce jeton fixe n'identifie personne en particulier,
    inadapté pour `created_by`."""
    x_app_token = request.headers.get("X-App-Token")
    if x_app_token:
        app_token = await AppTokenRepository(db).verify(x_app_token)
        if app_token is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Jeton invalide")
        return EphemeralIdentity(id=str(app_token.id), is_app_token=True)
    user = get_current_user(request)
    return EphemeralIdentity(id=user.user_id, is_app_token=False)
