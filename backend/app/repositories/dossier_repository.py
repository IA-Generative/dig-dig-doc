import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.analyse import Analyse
from app.models.conversation import Conversation, Message, MessageRole
from app.models.dossier import (
    Dossier,
    DossierDocument,
    DossierStatus,
    ExecutionStep,
    ExecutionStepKind,
    ExecutionStepStatus,
)
from app.repositories.analyse_repository import AnalyseRepository


class DossierRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._analyse_repository = AnalyseRepository(db)

    def _base_query(self):
        return select(Dossier).options(selectinload(Dossier.execution_steps), selectinload(Dossier.documents))

    async def list_all(self) -> Sequence[Dossier]:
        result = await self.db.execute(self._base_query().order_by(Dossier.created_at.desc()))
        return result.scalars().all()

    async def get(self, dossier_id: uuid.UUID) -> Dossier | None:
        result = await self.db.execute(self._base_query().where(Dossier.id == dossier_id))
        return result.scalar_one_or_none()

    async def create(self, *, name: str, analyse: Analyse) -> Dossier:
        dossier = Dossier(
            name=name,
            analyse_id=analyse.id,
            analyse_version=self._analyse_repository.get_version_label(analyse),
            status=DossierStatus.EN_ATTENTE,
        )
        self.db.add(dossier)
        await self.db.commit()
        await self.db.refresh(dossier)
        return dossier

    async def add_documents(self, dossier: Dossier, documents: list[dict]) -> None:
        for document in documents:
            self.db.add(
                DossierDocument(
                    dossier_id=dossier.id,
                    name=document["name"],
                    size=document["size"],
                    s3_key=document["s3_key"],
                    mimetype=document["mimetype"],
                )
            )
        await self.db.commit()
        await self.db.refresh(dossier)

    async def set_document_label(self, document: DossierDocument, label: str | None) -> None:
        document.label = label
        await self.db.commit()
        await self.db.refresh(document)

    async def get_document(self, dossier_id: uuid.UUID, document_id: uuid.UUID) -> DossierDocument | None:
        result = await self.db.execute(
            select(DossierDocument).where(DossierDocument.id == document_id, DossierDocument.dossier_id == dossier_id)
        )
        return result.scalar_one_or_none()

    def _conversation_query(self):
        # populate_existing: without it, re-querying a Conversation already in
        # the identity map (e.g. right after adding a message to it) would
        # keep the stale, already-loaded `messages` collection instead of
        # picking up the row just committed.
        return (
            select(Conversation).options(selectinload(Conversation.messages)).execution_options(populate_existing=True)
        )

    async def list_conversations(self, dossier_id: uuid.UUID, user_id: str) -> Sequence[Conversation]:
        result = await self.db.execute(
            self._conversation_query()
            .where(Conversation.dossier_id == dossier_id, Conversation.user_id == user_id)
            .order_by(Conversation.created_at)
        )
        return result.scalars().all()

    async def get_conversation(self, conversation_id: uuid.UUID) -> Conversation | None:
        result = await self.db.execute(self._conversation_query().where(Conversation.id == conversation_id))
        return result.scalar_one_or_none()

    async def create_conversation(self, dossier_id: uuid.UUID, user_id: str) -> Conversation:
        conversation = Conversation(dossier_id=dossier_id, user_id=user_id)
        self.db.add(conversation)
        await self.db.commit()
        await self.db.refresh(conversation)
        return await self.get_conversation(conversation.id)

    async def add_message(self, conversation: Conversation, role: MessageRole, content: str) -> Conversation:
        self.db.add(Message(conversation_id=conversation.id, role=role, content=content))
        await self.db.commit()
        return await self.get_conversation(conversation.id)

    async def launch(self, dossier: Dossier, analyse: Analyse) -> None:
        """Marks the dossier as running and lays down one execution step per
        stage (classification, extraction, one per agent). Actually
        producing a result for each step is the worker's job (issues #4/#5,
        not built yet) - this only records the intent to run."""
        if dossier.status == DossierStatus.EN_COURS:
            return

        now = datetime.now(UTC)
        for existing in list(dossier.execution_steps):
            await self.db.delete(existing)

        steps = [
            ExecutionStep(
                dossier_id=dossier.id,
                kind=ExecutionStepKind.CLASSIFICATION,
                label="Classification documentaire",
                status=ExecutionStepStatus.EN_COURS,
                started_at=now,
            ),
            ExecutionStep(
                dossier_id=dossier.id,
                kind=ExecutionStepKind.EXTRACTION,
                label="Extraction d'entités nommées",
                status=ExecutionStepStatus.EN_COURS,
                started_at=now,
            ),
        ]
        for agent in analyse.agents:
            steps.append(
                ExecutionStep(
                    dossier_id=dossier.id,
                    kind=ExecutionStepKind.AGENT,
                    label=agent.name,
                    status=ExecutionStepStatus.EN_COURS,
                    started_at=now,
                )
            )

        dossier.execution_steps = steps
        dossier.status = DossierStatus.EN_COURS
        dossier.analyse_version = self._analyse_repository.get_version_label(analyse)
        dossier.started_at = now
        dossier.ended_at = None
        await self.db.commit()
        await self.db.refresh(dossier)

    async def stop(self, dossier: Dossier) -> None:
        if dossier.status != DossierStatus.EN_COURS:
            return
        dossier.status = DossierStatus.ARRETE
        dossier.ended_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(dossier)
