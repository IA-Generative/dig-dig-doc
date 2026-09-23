import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.factory import RequestContext, get_current_user
from app.db import get_db
from app.repositories.app_token_repository import AppTokenRepository
from app.schemas.app_token import AppTokenCreate, AppTokenCreated, AppTokenOut
from app.schemas.pagination import Page

router = APIRouter(prefix="/app-tokens", tags=["App tokens"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=Page[AppTokenOut])
async def list_app_tokens(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Page[AppTokenOut]:
    tokens, total = await AppTokenRepository(db).list_paginated(page=page, page_size=page_size)
    return Page.of(list(tokens), total=total, page=page, page_size=page_size)


@router.post("", response_model=AppTokenCreated, status_code=status.HTTP_201_CREATED)
async def create_app_token(
    body: AppTokenCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
):
    app_token, token = await AppTokenRepository(db).create(name=body.name, created_by=user.user_id)
    return AppTokenCreated(
        id=app_token.id,
        name=app_token.name,
        created_by=app_token.created_by,
        created_at=app_token.created_at,
        revoked_at=app_token.revoked_at,
        last_used_at=app_token.last_used_at,
        token=token,
    )


@router.delete("/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_app_token(token_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]):
    repository = AppTokenRepository(db)
    app_token = await repository.get(token_id)
    if app_token is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Jeton introuvable")
    await repository.revoke(app_token)
