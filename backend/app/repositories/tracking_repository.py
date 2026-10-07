import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Literal

from sqlalchemy import Select, String, cast, extract, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analyse import Analyse, StatusDefinition
from app.models.app_user import AppUser
from app.models.dossier import Dossier
from app.models.dossier_event import DossierEvent, DossierEventType
from app.repositories.dossier_repository import DossierRepository
from app.services.dossier_access import visible_clause
from app.services.due_date import due_info, today_in_paris

if TYPE_CHECKING:
    from app.core.security.factory import RequestContext

SortKey = Literal["reference", "name", "analyse", "status", "assignee", "due", "created_at", "last_activity_at"]
StatusCategory = Literal["initial", "progress", "final"]


@dataclass(frozen=True)
class TrackingRow:
    dossier: Dossier
    analyse_name: str
    due: object
    last_activity_at: datetime


class TrackingRepository:
    """Lecture du tableau de suivi (issue #173) : filtres, recherche, tri et pagination **côté serveur**."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def _last_activity():
        """Dernière action du journal, hors consultations ; à défaut, la création du dossier."""
        latest = (
            select(func.max(DossierEvent.created_at))
            .where(DossierEvent.dossier_id == Dossier.id, DossierEvent.type != DossierEventType.CONSULTED.value)
            .correlate(Dossier)
            .scalar_subquery()
        )
        return func.coalesce(latest, Dossier.created_at)

    @staticmethod
    def _reference():
        """Même formule que `Dossier.reference`, pour pouvoir chercher et trier dessus."""
        year = cast(extract("year", func.timezone("UTC", Dossier.created_at)), String)
        return func.concat("DOS-", func.substr(year, 1, 4), "-", func.lpad(cast(Dossier.ref_number, String), 4, "0"))

    def _filters(
        self,
        *,
        analyse_ids: Sequence[uuid.UUID],
        status_id: uuid.UUID | None,
        category: StatusCategory | None,
        assignee: str | None,
        due: str | None,
        search: str | None,
        user: "RequestContext | None",
    ) -> list:
        # Le suivi porte sur les dossiers rangés dans une analyse : un dossier « à ranger » n'a ni statut ni seuils.
        filters: list = [Dossier.analyse_id.is_not(None)]
        # Seuls les dossiers visibles de la personne sont listés, et donc comptés et exportés (issue #177).
        if user is not None:
            filters.append(visible_clause(user.is_admin, user.groups))
        if analyse_ids:
            filters.append(Dossier.analyse_id.in_(analyse_ids))
        if status_id:
            filters.append(Dossier.workflow_status_id == status_id)
        if category == "initial":
            filters.append(StatusDefinition.is_initial.is_(True))
        elif category == "final":
            filters.append(StatusDefinition.is_final.is_(True))
        elif category == "progress":
            filters += [StatusDefinition.id.is_not(None), StatusDefinition.is_initial.is_(False)]
            filters.append(StatusDefinition.is_final.is_(False))
        if assignee == "none":
            filters.append(Dossier.assignee_id.is_(None))
        elif assignee:
            filters.append(Dossier.assignee_id == assignee)
        filters += DossierRepository._due_filters(due)
        if search and search.strip():
            escaped = search.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = f"%{escaped}%"
            filters.append(or_(Dossier.name.ilike(pattern, escape="\\"), self._reference().ilike(pattern, escape="\\")))
        return filters

    def _sort_columns(self, key: SortKey, descending: bool, last_activity) -> list:
        columns = {
            "reference": [Dossier.ref_number],
            "name": [func.lower(Dossier.name)],
            "analyse": [func.lower(Analyse.name)],
            "status": [StatusDefinition.position],
            "assignee": [func.lower(AppUser.name)],
            "due": [Dossier.due_at],
            "created_at": [Dossier.created_at],
            "last_activity_at": [last_activity],
        }[key]
        ordered = [column.desc() if descending else column.asc() for column in columns]
        # Les valeurs absentes (sans échéance, non affecté, sans statut) restent en dernier dans les deux sens.
        if key in ("status", "assignee", "due"):
            ordered = [column.nulls_last() for column in ordered]
        return [*ordered, Dossier.ref_number.desc()]

    async def list_rows(
        self,
        *,
        page: int,
        page_size: int,
        analyse_ids: Sequence[uuid.UUID] = (),
        status_id: uuid.UUID | None = None,
        category: StatusCategory | None = None,
        assignee: str | None = None,
        due: str | None = None,
        search: str | None = None,
        sort: SortKey = "created_at",
        descending: bool = True,
        user: "RequestContext | None" = None,
    ) -> tuple[list[TrackingRow], int]:
        last_activity = self._last_activity().label("last_activity_at")
        filters = self._filters(
            analyse_ids=analyse_ids,
            status_id=status_id,
            category=category,
            assignee=assignee,
            due=due,
            search=search,
            user=user,
        )

        def joined(statement: Select) -> Select:
            return (
                statement.join(Analyse, Analyse.id == Dossier.analyse_id)
                .outerjoin(StatusDefinition, StatusDefinition.id == Dossier.workflow_status_id)
                .outerjoin(AppUser, AppUser.user_id == Dossier.assignee_id)
                .where(*filters)
            )

        total = await self.db.scalar(joined(select(func.count()).select_from(Dossier)))
        query = joined(select(Dossier, Analyse.name, Analyse.due_thresholds, last_activity)).order_by(
            *self._sort_columns(sort, descending, self._last_activity())
        )
        result = await self.db.execute(query.limit(page_size).offset((page - 1) * page_size))
        today = today_in_paris()
        rows = [
            TrackingRow(
                dossier=dossier,
                analyse_name=analyse_name,
                due=due_info(dossier.due_at, thresholds, today, closed=dossier.closed_at is not None),
                last_activity_at=activity,
            )
            for dossier, analyse_name, thresholds, activity in result.all()
        ]
        return rows, total or 0
