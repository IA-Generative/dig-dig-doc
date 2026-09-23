import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.share_token import generate_token, hash_token
from app.models.app_token import AppToken


class AppTokenRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, *, name: str, created_by: str) -> tuple[AppToken, str]:
        token = generate_token()
        app_token = AppToken(name=name, token_hash=hash_token(token), created_by=created_by)
        self.db.add(app_token)
        await self.db.commit()
        await self.db.refresh(app_token)
        return app_token, token

    async def list_all(self) -> Sequence[AppToken]:
        result = await self.db.execute(select(AppToken).order_by(AppToken.created_at.desc()))
        return result.scalars().all()

    async def list_paginated(self, *, page: int, page_size: int) -> tuple[Sequence[AppToken], int]:
        total = await self.db.scalar(select(func.count()).select_from(AppToken))
        result = await self.db.execute(
            select(AppToken).order_by(AppToken.created_at.desc()).limit(page_size).offset((page - 1) * page_size)
        )
        return result.scalars().all(), total or 0

    async def get(self, token_id: uuid.UUID) -> AppToken | None:
        result = await self.db.execute(select(AppToken).where(AppToken.id == token_id))
        return result.scalar_one_or_none()

    async def revoke(self, app_token: AppToken) -> None:
        app_token.revoked_at = datetime.now(UTC)
        await self.db.commit()

    async def verify(self, token: str) -> AppToken | None:
        result = await self.db.execute(select(AppToken).where(AppToken.token_hash == hash_token(token)))
        app_token = result.scalar_one_or_none()
        if app_token is None or app_token.revoked_at is not None:
            return None
        app_token.last_used_at = datetime.now(UTC)
        await self.db.commit()
        return app_token
