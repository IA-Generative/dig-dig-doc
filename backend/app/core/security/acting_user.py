"""Agir au nom d'une personne (issue #222) : l'agent assistant n'a pas de session Keycloak, mais il ne doit jamais voir
plus de dossiers que la personne pour qui il travaille.

- **Serveur MCP** : le jeton d'application a un propriétaire (`created_by`) ; l'agent a les droits de cette personne.
- **Agent de l'interface** (worker) : il transmet l'auteur de la conversation dans `X-Acting-User`. Ces routes sont
  authentifiées par le jeton du worker, un service de confiance : l'en-tête n'est pas crédible venant d'ailleurs.

Les droits sont ceux que l'annuaire a vus à la **dernière connexion** de la personne (groupes, rôle administrateur).
Une personne inconnue de l'annuaire, ou sans identité transmise, n'a **aucun groupe** : elle ne voit que les dossiers
« selon l'analyse »."""

import uuid
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.factory import RequestContext
from app.db import get_db
from app.models.app_token import AppToken
from app.models.app_user import AppUser


async def _owner_of_token(db: AsyncSession, token_id: str) -> str | None:
    """Une conversation ouverte par le serveur MCP est signée du jeton d'application : on remonte à son propriétaire."""
    try:
        app_token = await db.get(AppToken, uuid.UUID(token_id))
    except ValueError:
        return None
    return app_token.created_by if app_token else None


async def context_for_user(db: AsyncSession, user_id: str | None) -> RequestContext:
    person = await db.get(AppUser, user_id) if user_id else None
    if person is None and user_id:
        owner = await _owner_of_token(db, user_id)
        person = await db.get(AppUser, owner) if owner else None
    if person is None:
        return RequestContext(user_id=user_id or "unknown", email="", roles=[], is_admin=False, groups=[])
    return RequestContext(
        user_id=person.user_id,
        email=person.email,
        roles=["admin"] if person.is_admin else [],
        is_admin=person.is_admin,
        first_name=person.name,
        last_name="",
        groups=list(person.groups),
    )


async def acting_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    x_acting_user: Annotated[str | None, Header(description="Identifiant de la personne pour qui l'agent agit")] = None,
) -> RequestContext:
    """Dépendance des routes internes de l'agent : les droits de la personne transmise (ou aucun droit)."""
    return await context_for_user(db, x_acting_user)
