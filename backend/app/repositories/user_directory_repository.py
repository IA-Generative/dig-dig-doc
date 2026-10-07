from collections.abc import Sequence
from typing import TYPE_CHECKING

from sqlalchemy import false, func, or_, select
from sqlalchemy.dialects.postgresql import array, insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.app_user import AppUser
from app.models.dossier_access import Visibility

if TYPE_CHECKING:
    from app.core.security.factory import RequestContext


def display_name(user: "RequestContext") -> str:
    return f"{user.first_name} {user.last_name}".strip() or user.email or user.user_id


class UserDirectoryRepository:
    """Annuaire local (issue #173) : qui peut recevoir un dossier. Alimenté à la connexion, jamais à la main."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def touch(self, user: "RequestContext") -> None:
        """Enregistre ou met à jour la personne connectée (nom, e-mail, groupes, rôle, dernière connexion)."""
        statement = insert(AppUser).values(
            user_id=user.user_id,
            name=display_name(user),
            email=user.email or "",
            groups=list(user.groups),
            is_admin=user.is_admin,
        )
        await self.db.execute(
            statement.on_conflict_do_update(
                index_elements=[AppUser.user_id],
                set_={
                    "name": statement.excluded.name,
                    "email": statement.excluded.email,
                    "groups": statement.excluded.groups,
                    "is_admin": statement.excluded.is_admin,
                    "last_seen_at": func.now(),
                },
            )
        )
        await self.db.commit()

    async def get(self, user_id: str) -> AppUser | None:
        return await self.db.get(AppUser, user_id)

    async def search(
        self, query: str | None, limit: int, *, entitled_to: tuple[str, bool, Sequence[str]] | None = None
    ) -> Sequence[AppUser]:
        """Personnes connues, par nom ; ``query`` filtre sur le nom ou l'e-mail (sans casse). ``entitled_to`` =
        (visibilité, a une analyse, groupes du dossier) : ne garde que les personnes qui ont accès au dossier, selon
        l'annuaire (issue #177) ; même règle que `can_view`."""
        statement = select(AppUser).order_by(func.lower(AppUser.name), AppUser.user_id).limit(limit)
        if entitled_to is not None:
            visibility, has_analyse, dossier_groups = entitled_to
            if not (visibility == Visibility.ANALYSE.value and has_analyse):
                by_group = AppUser.groups.has_any(array(list(dossier_groups))) if dossier_groups else false()
                statement = statement.where(or_(AppUser.is_admin.is_(True), by_group))
        if query and query.strip():
            escaped = query.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = f"%{escaped}%"
            statement = statement.where(
                or_(AppUser.name.ilike(pattern, escape="\\"), AppUser.email.ilike(pattern, escape="\\"))
            )
        return (await self.db.execute(statement)).scalars().all()
