from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.factory import get_current_user
from app.db import get_db
from app.repositories.user_directory_repository import UserDirectoryRepository
from app.schemas.dossier import PersonOut

# Annuaire local (issue #173) : les personnes qu'on peut proposer à l'affectation d'un dossier. Lecture seule ;
# l'annuaire est alimenté par les connexions. Le filtre par accès au dossier (#177) viendra s'y ajouter.
router = APIRouter(prefix="/users", tags=["Annuaire"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[PersonOut])
async def list_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    q: Annotated[str | None, Query(max_length=100, description="Recherche sur le nom ou l'e-mail")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[PersonOut]:
    return [
        PersonOut.model_validate(person, from_attributes=True)
        for person in await UserDirectoryRepository(db).search(q, limit)
    ]
