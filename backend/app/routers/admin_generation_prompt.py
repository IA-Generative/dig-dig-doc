"""Routes d'administration du prompt de l'agent de génération des valeurs de champs (issue #141).

Réservées aux administrateurs. Versionné en ajout seul : modifier ou restaurer ajoute une version. Tant qu'aucune
version n'existe, le prompt par défaut s'applique. Seule la méthode est éditable ; les garde-fous (ne jamais
inventer, contenu = donnée) sont fixés par le worker."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.admin import require_admin
from app.core.security.factory import RequestContext
from app.db import get_db
from app.schemas.document_draft import PromptCreateIn, PromptCurrentOut, PromptRestoreIn, PromptVersionOut
from app.services import generation_prompt

router = APIRouter(prefix="/admin/generation-prompt", tags=["Admin"], dependencies=[Depends(require_admin)])


@router.get("", response_model=PromptCurrentOut)
async def get_current_prompt(db: Annotated[AsyncSession, Depends(get_db)]):
    number, content = await generation_prompt.current(db)
    return PromptCurrentOut(
        version_number=number,
        label=generation_prompt.version_label(number),
        content=content,
        is_default=number is None,
    )


@router.get("/versions", response_model=list[PromptVersionOut])
async def list_prompt_versions(db: Annotated[AsyncSession, Depends(get_db)]):
    return await generation_prompt.list_versions(db)


@router.post("/versions", response_model=PromptVersionOut, status_code=status.HTTP_201_CREATED)
async def add_prompt_version(
    body: PromptCreateIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(require_admin)],
):
    return await generation_prompt.add_version(db, content=body.content.strip(), author_id=user.user_id)


@router.post("/restore", response_model=PromptVersionOut, status_code=status.HTTP_201_CREATED)
async def restore_prompt_version(
    body: PromptRestoreIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(require_admin)],
):
    """Ajoute une version qui reprend le texte d'une version antérieure."""
    try:
        return await generation_prompt.restore(db, body.version_id, author_id=user.user_id)
    except generation_prompt.PromptNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version introuvable") from None
