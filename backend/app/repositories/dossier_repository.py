import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.analyse import Analyse
from app.models.conversation import Conversation, Message, MessageRole, MessageSource
from app.models.document_page import (
    BoundingBox,
    DocumentPage,
    DocumentPrediction,
    PredictionKind,
    PredictionValidation,
    PredictionValidationStatus,
)
from app.models.dossier import (
    Dossier,
    DossierDocument,
    DossierStatus,
    ExecutionStep,
    ExecutionStepKind,
    ExecutionStepStatus,
)
from app.models.execution_log import ExecutionLog, ExecutionLogLevel
from app.repositories.analyse_repository import AnalyseRepository


class DossierRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._analyse_repository = AnalyseRepository(db)

    def _base_query(self):
        pages_load = selectinload(Dossier.documents).selectinload(DossierDocument.pages)
        predictions_load = pages_load.selectinload(DocumentPage.predictions)
        return (
            select(Dossier)
            .options(
                selectinload(Dossier.execution_steps).selectinload(ExecutionStep.logs),
                pages_load.selectinload(DocumentPage.bounding_boxes),
                predictions_load.selectinload(DocumentPrediction.bounding_box),
                predictions_load.selectinload(DocumentPrediction.validations).selectinload(
                    PredictionValidation.bounding_box
                ),
                # populate_existing: nécessaire pour le SSE (/dossiers/{id}/stream),
                # qui réinterroge en boucle sur la même session - sans ça, une
                # fois le Dossier chargé une première fois, les requêtes
                # suivantes renverraient l'objet du cache d'identité, pas l'état
                # réellement en base.
            )
            .execution_options(populate_existing=True)
        )

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
        # Pas de refresh(document) : réexpirerait `pages` (déjà chargée par
        # get_document) et redéclencherait un lazy-load hors contexte async.

    def _conversation_query(self):
        # populate_existing: without it, re-querying a Conversation already in
        # the identity map (e.g. right after adding a message to it) would
        # keep the stale, already-loaded `messages` collection instead of
        # picking up the row just committed.
        return (
            select(Conversation)
            .options(selectinload(Conversation.messages).selectinload(Message.sources))
            .execution_options(populate_existing=True)
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

    async def add_message(
        self, conversation: Conversation, role: MessageRole, content: str, sources: list[dict] | None = None
    ) -> Conversation:
        message = Message(conversation_id=conversation.id, role=role, content=content)
        self.db.add(message)
        await self.db.flush()
        for source in sources or []:
            self.db.add(
                MessageSource(
                    message_id=message.id,
                    dossier_document_id=source.get("dossier_document_id"),
                    execution_step_id=source.get("execution_step_id"),
                    excerpt=source.get("excerpt"),
                )
            )
        await self.db.commit()
        return await self.get_conversation(conversation.id)

    # --- Logs et callback de fin d'étape (appelés par le worker) ---

    async def get_execution_step(self, dossier_id: uuid.UUID, step_id: uuid.UUID) -> ExecutionStep | None:
        result = await self.db.execute(
            select(ExecutionStep)
            .options(selectinload(ExecutionStep.logs))
            .where(ExecutionStep.id == step_id, ExecutionStep.dossier_id == dossier_id)
            .execution_options(populate_existing=True)
        )
        return result.scalar_one_or_none()

    async def get_execution_step_by_id(self, step_id: uuid.UUID) -> ExecutionStep | None:
        result = await self.db.execute(
            select(ExecutionStep)
            .options(selectinload(ExecutionStep.logs))
            .where(ExecutionStep.id == step_id)
            .execution_options(populate_existing=True)
        )
        return result.scalar_one_or_none()

    async def add_log(self, step: ExecutionStep, level: ExecutionLogLevel, message: str) -> ExecutionStep:
        self.db.add(ExecutionLog(execution_step_id=step.id, level=level, message=message))
        await self.db.commit()
        return await self.get_execution_step(step.dossier_id, step.id)

    async def complete_execution_step(
        self, step: ExecutionStep, status: ExecutionStepStatus, output: str | None
    ) -> ExecutionStep:
        step.status = status
        step.output = output
        step.ended_at = datetime.now(UTC)
        await self.db.commit()
        # Pas de refresh(step) : réexpirerait `logs` (déjà chargée par
        # get_execution_step_by_id) et redéclencherait un lazy-load hors
        # contexte async à la sérialisation - même raison que add_page.
        return step

    # --- Pages, prédictions et validation humaine ---

    async def get_document(self, dossier_id: uuid.UUID, document_id: uuid.UUID) -> DossierDocument | None:
        pages_load = selectinload(DossierDocument.pages)
        predictions_load = pages_load.selectinload(DocumentPage.predictions)
        result = await self.db.execute(
            select(DossierDocument)
            .options(
                pages_load.selectinload(DocumentPage.bounding_boxes),
                predictions_load.selectinload(DocumentPrediction.bounding_box),
                predictions_load.selectinload(DocumentPrediction.validations).selectinload(
                    PredictionValidation.bounding_box
                ),
            )
            .where(DossierDocument.id == document_id, DossierDocument.dossier_id == dossier_id)
            .execution_options(populate_existing=True)
        )
        return result.scalar_one_or_none()

    async def get_document_by_id(self, document_id: uuid.UUID) -> DossierDocument | None:
        result = await self.db.execute(select(DossierDocument).where(DossierDocument.id == document_id))
        return result.scalar_one_or_none()

    async def add_page(
        self,
        document: DossierDocument,
        *,
        page_number: int,
        width: int | None,
        height: int | None,
        content: str | None,
    ) -> DocumentPage:
        page = DocumentPage(
            dossier_document_id=document.id,
            page_number=page_number,
            width=width,
            height=height,
            content=content,
            predictions=[],
            bounding_boxes=[],
        )
        self.db.add(page)
        await self.db.commit()
        # Pas de refresh(page) : redéclencherait un lazy-load de
        # `predictions`/`bounding_boxes` hors contexte async (MissingGreenlet)
        # - voir le commentaire équivalent dans launch(). L'id généré côté
        # client (UUIDMixin.default) est déjà à jour après le commit.
        return page

    def _page_options(self):
        predictions_load = selectinload(DocumentPage.predictions)
        return (
            selectinload(DocumentPage.bounding_boxes),
            predictions_load.selectinload(DocumentPrediction.bounding_box),
            predictions_load.selectinload(DocumentPrediction.validations).selectinload(
                PredictionValidation.bounding_box
            ),
        )

    async def get_page(self, document_id: uuid.UUID, page_id: uuid.UUID) -> DocumentPage | None:
        result = await self.db.execute(
            select(DocumentPage)
            .options(*self._page_options())
            .where(DocumentPage.id == page_id, DocumentPage.dossier_document_id == document_id)
            .execution_options(populate_existing=True)
        )
        return result.scalar_one_or_none()

    async def get_page_by_id(self, page_id: uuid.UUID) -> DocumentPage | None:
        result = await self.db.execute(
            select(DocumentPage)
            .options(*self._page_options())
            .where(DocumentPage.id == page_id)
            .execution_options(populate_existing=True)
        )
        return result.scalar_one_or_none()

    async def add_bounding_box(
        self, page: DocumentPage, *, x_min: float, y_min: float, x_max: float, y_max: float
    ) -> BoundingBox:
        bbox = BoundingBox(document_page_id=page.id, x_min=x_min, y_min=y_min, x_max=x_max, y_max=y_max)
        self.db.add(bbox)
        await self.db.flush()
        return bbox

    async def add_prediction(
        self,
        page: DocumentPage,
        *,
        kind: PredictionKind,
        name: str,
        value: str,
        confidence: float | None,
        bounding_box: dict | None,
    ) -> DocumentPrediction:
        bbox = await self.add_bounding_box(page, **bounding_box) if bounding_box else None
        prediction = DocumentPrediction(
            document_page_id=page.id,
            kind=kind,
            name=name,
            value=value,
            confidence=confidence,
            bounding_box=bbox,
            validations=[],
        )
        self.db.add(prediction)
        await self.db.commit()
        # Pas de refresh(prediction) : même raison que pour add_page ci-dessus.
        return prediction

    def _prediction_options(self):
        return (
            selectinload(DocumentPrediction.bounding_box),
            selectinload(DocumentPrediction.validations).selectinload(PredictionValidation.bounding_box),
        )

    async def get_prediction(self, page_id: uuid.UUID, prediction_id: uuid.UUID) -> DocumentPrediction | None:
        result = await self.db.execute(
            select(DocumentPrediction)
            .options(*self._prediction_options())
            .where(DocumentPrediction.id == prediction_id, DocumentPrediction.document_page_id == page_id)
            .execution_options(populate_existing=True)
        )
        return result.scalar_one_or_none()

    async def get_prediction_by_id(self, prediction_id: uuid.UUID) -> DocumentPrediction | None:
        result = await self.db.execute(
            select(DocumentPrediction)
            .options(*self._prediction_options())
            .where(DocumentPrediction.id == prediction_id)
            .execution_options(populate_existing=True)
        )
        return result.scalar_one_or_none()

    async def add_prediction_validation(
        self,
        prediction: DocumentPrediction,
        *,
        validator_user_id: str,
        status: PredictionValidationStatus,
        corrected_value: str | None,
        bounding_box: dict | None,
    ) -> DocumentPrediction:
        # Toujours une nouvelle BoundingBox, jamais une mutation de celle de
        # la prédiction d'origine (ou d'une validation précédente) : l'idée
        # est de garder l'historique intact, comme le reste de
        # PredictionValidation.
        bbox = BoundingBox(document_page_id=prediction.document_page_id, **bounding_box) if bounding_box else None
        self.db.add(
            PredictionValidation(
                prediction_id=prediction.id,
                validator_user_id=validator_user_id,
                status=status,
                corrected_value=corrected_value,
                bounding_box=bbox,
            )
        )
        await self.db.commit()
        return await self.get_prediction(prediction.document_page_id, prediction.id)

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
                logs=[],
            ),
            ExecutionStep(
                dossier_id=dossier.id,
                kind=ExecutionStepKind.EXTRACTION,
                label="Extraction d'entités nommées",
                status=ExecutionStepStatus.EN_COURS,
                started_at=now,
                logs=[],
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
                    logs=[],
                )
            )

        dossier.execution_steps = steps
        dossier.status = DossierStatus.EN_COURS
        dossier.analyse_version = self._analyse_repository.get_version_label(analyse)
        dossier.started_at = now
        dossier.ended_at = None
        await self.db.commit()
        # Pas de refresh(dossier) ici : ça re-déclencherait un lazy-load des
        # nouvelles execution_steps (et de leur relation `logs`, vide mais
        # non chargée) en dehors du contexte async - MissingGreenlet. Les
        # objets Python déjà en mémoire (avec logs=[] posé plus haut) et
        # leurs id générés côté client (UUIDMixin.default) sont à jour après
        # le commit (expire_on_commit=False sur la session).

    async def stop(self, dossier: Dossier) -> None:
        if dossier.status != DossierStatus.EN_COURS:
            return
        dossier.status = DossierStatus.ARRETE
        dossier.ended_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(dossier)
