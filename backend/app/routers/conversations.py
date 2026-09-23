from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.factory import RequestContext, get_current_user
from app.db import get_db
from app.repositories.dossier_repository import DossierRepository
from app.schemas.dossier import ConversationSummaryOut

router = APIRouter(prefix="/conversations", tags=["Conversations"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[ConversationSummaryOut])
async def list_my_conversations(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
):
    """Toutes les conversations de l'utilisateur courant, tous dossiers
    confondus - pour la liste façon ChatGPT dans la sidebar. Rien à passer
    en paramètre : list_conversations_for_user filtre déjà par
    user.user_id, jamais un id fourni par le client."""
    return await DossierRepository(db).list_conversations_for_user(user.user_id)
