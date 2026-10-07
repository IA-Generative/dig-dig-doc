import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.factory import RequestContext, get_current_user
from app.db import get_db
from app.repositories.tracking_repository import SortKey, StatusCategory, TrackingRepository
from app.schemas.analyse import StatusDefinitionOut
from app.schemas.dossier import DueInfoOut, PersonOut
from app.schemas.pagination import Page
from app.schemas.tracking import TrackingAnalyseOut, TrackingRowOut

# Tableau de suivi (issue #173) : la même route sert l'onglet « Suivi » d'une analyse (`analyse_id`) et la vue
# transversale (aucun `analyse_id`). Les dossiers « à ranger » n'y figurent pas.
router = APIRouter(prefix="/tracking", tags=["Suivi"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=Page[TrackingRowOut])
async def list_tracking(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    analyse_id: Annotated[
        list[uuid.UUID] | None, Query(description="Une ou plusieurs analyses ; aucune = toutes")
    ] = None,
    status_id: Annotated[uuid.UUID | None, Query(description="Un statut précis")] = None,
    status_category: Annotated[
        StatusCategory | None,
        Query(description="Regroupement commun à toutes les analyses : initial, progress (en cours) ou final"),
    ] = None,
    assignee: Annotated[
        str | None, Query(description="me (moi), none (non affectés) ou l'identifiant d'une personne")
    ] = None,
    due: Annotated[
        str | None,
        Query(pattern="^(overdue|7|30|none)$", description="overdue, 7 ou 30 (jours restants au plus), none"),
    ] = None,
    search: Annotated[str | None, Query(max_length=100, description="Nom ou référence du dossier")] = None,
    sort: SortKey = "created_at",
    direction: Annotated[str, Query(pattern="^(asc|desc)$")] = "desc",
) -> Page[TrackingRowOut]:
    rows, total = await TrackingRepository(db).list_rows(
        page=page,
        page_size=page_size,
        analyse_ids=analyse_id or [],
        status_id=status_id,
        category=status_category,
        assignee=user.user_id if assignee == "me" else assignee,
        due=due,
        search=search,
        sort=sort,
        descending=direction == "desc",
        user=user,
    )
    items = [
        TrackingRowOut(
            id=row.dossier.id,
            reference=row.dossier.reference,
            name=row.dossier.name,
            analyse=TrackingAnalyseOut(id=row.dossier.analyse_id, name=row.analyse_name),
            status=row.dossier.workflow_status and StatusDefinitionOut.model_validate(row.dossier.workflow_status),
            assignee=row.dossier.assignee and PersonOut.model_validate(row.dossier.assignee, from_attributes=True),
            due_at=row.dossier.due_at,
            due=row.due and DueInfoOut.model_validate(row.due, from_attributes=True),
            created_at=row.dossier.created_at,
            last_activity_at=row.last_activity_at,
        )
        for row in rows
    ]
    return Page.of(items, total=total, page=page, page_size=page_size)
