import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.factory import RequestContext, get_current_user
from app.db import get_db
from app.repositories.analyse_repository import AnalyseRepository
from app.repositories.tracking_repository import SortKey, StatusCategory, TrackingRepository
from app.schemas.analyse import StatusDefinitionOut
from app.schemas.dossier import DueInfoOut, PersonOut
from app.schemas.pagination import Page
from app.schemas.tracking import TrackingAnalyseOut, TrackingRowOut
from app.services.custom_fields import FieldFilterError, current_values, parse_field_filters

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
    access: Annotated[
        Literal["restricted", "analyse"] | None, Query(description="Visibilité : restreints, ou selon l'analyse")
    ] = None,
    field_filters: Annotated[
        str | None,
        Query(
            max_length=4000,
            description="Filtres de colonnes personnalisées, un objet JSON {identifiant du champ: texte ou "
            "{min, max}} ; une seule analyse (analyse_id) est exigée",
        ),
    ] = None,
    sort: SortKey = "created_at",
    sort_field: Annotated[
        str | None, Query(max_length=40, description="Avec sort=field : identifiant de la colonne personnalisée")
    ] = None,
    direction: Annotated[str, Query(pattern="^(asc|desc)$")] = "desc",
) -> Page[TrackingRowOut]:
    parsed_filters: list = []
    sort_definition = None
    if field_filters or sort == "field":
        # Les colonnes personnalisées sont propres à une analyse : on filtre ou on trie sur une seule à la fois.
        if len(analyse_id or []) != 1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "code": "single_analyse_required",
                    "message": "Les colonnes personnalisées dépendent de l'analyse : choisissez-en une seule.",
                },
            )
        analyse = await AnalyseRepository(db).get(analyse_id[0])
        fields = analyse.custom_fields if analyse else []
        try:
            parsed_filters = parse_field_filters(field_filters, fields)
        except FieldFilterError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={"code": "invalid_field_filter", "message": str(error)},
            ) from error
        if sort == "field":
            sort_definition = next((f for f in fields if f["id"] == sort_field), None)
            if sort_definition is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail={"code": "unknown_field", "message": "Colonne inconnue pour cette analyse."},
                )
    rows, total = await TrackingRepository(db).list_rows(
        page=page,
        page_size=page_size,
        analyse_ids=analyse_id or [],
        status_id=status_id,
        category=status_category,
        assignee=user.user_id if assignee == "me" else assignee,
        due=due,
        search=search,
        access=access,
        field_filters=parsed_filters,
        sort=sort,
        sort_field=sort_definition,
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
            visibility=row.dossier.visibility,
            due_at=row.dossier.due_at,
            due=row.due and DueInfoOut.model_validate(row.due, from_attributes=True),
            created_at=row.dossier.created_at,
            last_activity_at=row.last_activity_at,
            values=current_values(row.fields, row.dossier.custom_values),
        )
        for row in rows
    ]
    return Page.of(items, total=total, page=page, page_size=page_size)
