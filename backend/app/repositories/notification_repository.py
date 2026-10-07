import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.analyse import Analyse
from app.models.dossier import Dossier
from app.models.dossier_event import DossierEvent, DossierEventType
from app.models.notification import Notification, NotificationCursor
from app.services.due_date import due_info, today_in_paris
from app.services.notification_messages import (
    CATEGORIES,
    KIND_CATEGORY,
    analysis_message,
    assigned_message,
    due_message,
    kinds_of,
    status_changed_message,
)

# Au premier passage d'une personne, on remonte le journal de cette durée (pas plus : pas de déluge d'anciennetés).
FIRST_SYNC_DAYS = 7
# Notifications lues gardées 90 jours, puis purgées. Les non lues restent.
READ_RETENTION_DAYS = 90
MAX_EVENTS_PER_SYNC = 200
MAX_DUE_PER_SYNC = 50


class NotificationRepository:
    """Notifications d'une personne (issue #174). Elles se fabriquent **à la lecture** : `sync` lit ce que le journal
    (#169) a enregistré depuis la dernière fois, et l'état des échéances, puis écrit ce qui est nouveau. Pas de
    tâche planifiée : une notification n'a d'utilité que lorsque la personne ouvre l'application. Chaque méthode est
    **bornée à un destinataire** : rien ne lit ni ne modifie la notification d'un autre."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # --- Génération ---

    async def sync(self, user_id: str, now: datetime | None = None) -> None:
        now = now or datetime.now(UTC)
        cursor = await self.db.get(NotificationCursor, user_id)
        first = cursor is None
        max_seq = await self.db.scalar(select(func.coalesce(func.max(DossierEvent.seq), 0)))

        rows = await self._event_notifications(user_id, cursor.last_seq if cursor else None, max_seq, now)
        rows += await self._due_notifications(user_id, now, already_read=first)
        if rows:
            await self.db.execute(
                insert(Notification).values(rows).on_conflict_do_nothing(constraint="uq_notifications_user_dedup")
            )

        cursor_statement = insert(NotificationCursor).values(user_id=user_id, last_seq=max_seq)
        await self.db.execute(
            cursor_statement.on_conflict_do_update(
                index_elements=[NotificationCursor.user_id], set_={"last_seq": cursor_statement.excluded.last_seq}
            )
        )
        await self.db.execute(
            delete(Notification).where(
                Notification.user_id == user_id, Notification.read_at < now - timedelta(days=READ_RETENTION_DAYS)
            )
        )
        await self.db.commit()

    async def _event_notifications(self, user_id: str, last_seq: int | None, max_seq: int, now: datetime) -> list[dict]:
        started = aliased(DossierEvent)
        # La personne qui a lancé l'analyse : l'auteur du dernier « analyse lancée » avant la fin.
        launcher = (
            select(started.actor_id)
            .where(
                started.dossier_id == DossierEvent.dossier_id,
                started.type == DossierEventType.ANALYSIS_STARTED.value,
                started.seq < DossierEvent.seq,
            )
            .order_by(started.seq.desc())
            .limit(1)
            .correlate(DossierEvent)
            .scalar_subquery()
        )
        window = (
            DossierEvent.created_at >= now - timedelta(days=FIRST_SYNC_DAYS)
            if last_seq is None
            else DossierEvent.seq > last_seq
        )
        # On n'est jamais notifié de sa propre action.
        by_someone_else = DossierEvent.actor_id.is_distinct_from(user_id)
        result = await self.db.execute(
            select(DossierEvent, Dossier.name)
            .join(Dossier, Dossier.id == DossierEvent.dossier_id)
            .where(
                window,
                DossierEvent.seq <= max_seq,
                or_(
                    and_(
                        DossierEvent.type == DossierEventType.ASSIGNEE_CHANGED.value,
                        DossierEvent.payload["to"]["id"].as_string() == user_id,
                        by_someone_else,
                    ),
                    and_(
                        DossierEvent.type == DossierEventType.STATUS_CHANGED.value,
                        Dossier.assignee_id == user_id,
                        by_someone_else,
                    ),
                    and_(
                        DossierEvent.type.in_(
                            [DossierEventType.ANALYSIS_FINISHED.value, DossierEventType.ANALYSIS_FAILED.value]
                        ),
                        launcher == user_id,
                    ),
                ),
            )
            .order_by(DossierEvent.seq)
            .limit(MAX_EVENTS_PER_SYNC)
        )
        rows = []
        for event, dossier_name in result.all():
            if event.type == DossierEventType.ASSIGNEE_CHANGED.value:
                kind, message = "assigned", assigned_message(event.actor_name)
            elif event.type == DossierEventType.STATUS_CHANGED.value:
                kind = "status_changed"
                message = status_changed_message((event.payload.get("to") or {}).get("name", ""), event.actor_name)
            else:
                failed = event.type == DossierEventType.ANALYSIS_FAILED.value
                kind, message = ("analysis_failed" if failed else "analysis_done"), analysis_message(failed)
            rows.append(
                {
                    "id": uuid.uuid4(),
                    "user_id": user_id,
                    "kind": kind,
                    "dossier_id": event.dossier_id,
                    "dossier_name": dossier_name,
                    "message": message,
                    "dedup_key": f"event:{event.id}",
                    "created_at": event.created_at,
                    "read_at": None,
                }
            )
        return rows

    async def _due_notifications(self, user_id: str, now: datetime, *, already_read: bool) -> list[dict]:
        """Une notification par dossier ouvert qui entre dans un niveau d'échéance (proche, dépassée), **une seule
        fois par niveau et par date d'échéance**. Au premier passage, l'état existant est enregistré comme déjà lu :
        l'agenda l'affiche déjà, inutile d'en faire un déluge de notifications."""
        result = await self.db.execute(
            select(Dossier, Analyse.due_thresholds)
            .join(Analyse, Analyse.id == Dossier.analyse_id)
            .where(Dossier.assignee_id == user_id, Dossier.closed_at.is_(None), Dossier.due_at.is_not(None))
            .order_by(Dossier.due_at, Dossier.ref_number)
        )
        today = today_in_paris(now)
        rows = []
        for dossier, thresholds in result.all():
            info = due_info(dossier.due_at, thresholds, today)
            if info is None or info.level not in ("soon", "overdue"):
                continue
            rows.append(
                {
                    "id": uuid.uuid4(),
                    "user_id": user_id,
                    "kind": "overdue" if info.level == "overdue" else "due_soon",
                    "dossier_id": dossier.id,
                    "dossier_name": dossier.name,
                    "message": due_message(info.level, info.days_left),
                    "dedup_key": f"due:{dossier.id}:{info.level}:{dossier.due_at.isoformat()}",
                    "created_at": now,
                    "read_at": now if already_read else None,
                }
            )
            if len(rows) >= MAX_DUE_PER_SYNC:
                break
        return rows

    # --- Lecture ---

    async def list_for(
        self, user_id: str, *, category: str | None = None, unread_only: bool = False, limit: int = 100
    ) -> Sequence[Notification]:
        statement = select(Notification).where(Notification.user_id == user_id)
        if category:
            statement = statement.where(Notification.kind.in_(kinds_of(category)))
        if unread_only:
            statement = statement.where(Notification.read_at.is_(None))
        result = await self.db.execute(statement.order_by(Notification.created_at.desc(), Notification.id).limit(limit))
        return result.scalars().all()

    async def unread_counts(self, user_id: str) -> tuple[int, dict[str, int]]:
        result = await self.db.execute(
            select(Notification.kind, func.count())
            .where(Notification.user_id == user_id, Notification.read_at.is_(None))
            .group_by(Notification.kind)
        )
        by_category = dict.fromkeys(CATEGORIES, 0)
        for kind, count in result.all():
            by_category[KIND_CATEGORY[kind]] += count
        return sum(by_category.values()), by_category

    # --- Écriture ---

    async def mark_read(self, user_id: str, notification_id: uuid.UUID) -> bool:
        """Marque lue (une fois) ; ``False`` si elle n'existe pas ou n'est pas à cette personne."""
        owned = await self.db.scalar(
            select(Notification.id).where(Notification.id == notification_id, Notification.user_id == user_id)
        )
        if owned is None:
            return False
        await self.db.execute(
            update(Notification)
            .where(Notification.id == notification_id, Notification.read_at.is_(None))
            .values(read_at=func.now())
        )
        await self.db.commit()
        return True

    async def mark_all_read(self, user_id: str, category: str | None = None) -> int:
        statement = update(Notification).where(Notification.user_id == user_id, Notification.read_at.is_(None))
        if category:
            statement = statement.where(Notification.kind.in_(kinds_of(category)))
        result = await self.db.execute(statement.values(read_at=func.now()))
        await self.db.commit()
        return result.rowcount
