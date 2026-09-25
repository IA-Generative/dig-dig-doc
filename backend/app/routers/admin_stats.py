from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.factory import RequestContext, get_current_user
from app.db import get_db
from app.models.agent_conversation import AgentConversation, AgentMessage
from app.models.analyse import Analyse
from app.models.conversation import Conversation, Message
from app.models.dossier import Dossier
from app.models.report import Report
from app.models.user_preference import UserPreference

router = APIRouter(prefix="/admin/stats", tags=["Admin"], dependencies=[Depends(get_current_user)])


def _require_admin(user: RequestContext) -> None:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès réservé aux administrateurs")


@router.get("")
async def get_platform_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
) -> dict:
    """Statistiques globales de la plateforme (admin seulement)."""
    _require_admin(user)

    # Compteurs simples
    analyses_count = await db.scalar(select(func.count()).select_from(Analyse))
    dossiers_count = await db.scalar(select(func.count()).select_from(Dossier))
    conversations_count = await db.scalar(select(func.count()).select_from(Conversation))
    messages_count = await db.scalar(select(func.count()).select_from(Message))
    agent_conversations_count = await db.scalar(select(func.count()).select_from(AgentConversation))
    agent_messages_count = await db.scalar(select(func.count()).select_from(AgentMessage))
    reports_count = await db.scalar(select(func.count()).select_from(Report))
    users_count = await db.scalar(select(func.count()).select_from(UserPreference))

    # Dossiers par statut
    status_rows = (
        await db.execute(
            select(Dossier.status, func.count()).group_by(Dossier.status)
        )
    ).all()
    dossiers_by_status = {row[0].value if hasattr(row[0], "value") else str(row[0]): row[1] for row in status_rows}

    # Créations par jour (7 derniers jours)
    seven_days_ago = datetime.now(UTC) - timedelta(days=7)
    daily_dossiers = (
        await db.execute(
            select(func.date_trunc("day", Dossier.created_at).label("day"), func.count())
            .where(Dossier.created_at >= seven_days_ago)
            .group_by("day")
            .order_by("day")
        )
    ).all()
    daily_creations = [
        {"date": row[0].isoformat() if row[0] else None, "count": row[1]} for row in daily_dossiers
    ]

    # Top modèles LLM utilisés (dans les conversations de dossier)
    model_rows = (
        await db.execute(
            select(Conversation.model, func.count())
            .where(Conversation.model.isnot(None))
            .group_by(Conversation.model)
            .order_by(func.count().desc())
            .limit(10)
        )
    ).all()
    top_models = [{"model": row[0], "count": row[1]} for row in model_rows]

    return {
        "analyses_count": analyses_count or 0,
        "dossiers_count": dossiers_count or 0,
        "conversations_count": conversations_count or 0,
        "messages_count": messages_count or 0,
        "agent_conversations_count": agent_conversations_count or 0,
        "agent_messages_count": agent_messages_count or 0,
        "reports_count": reports_count or 0,
        "users_count": users_count or 0,
        "dossiers_by_status": dossiers_by_status,
        "daily_creations": daily_creations,
        "top_models": top_models,
    }
