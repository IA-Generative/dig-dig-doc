import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.chat_event import ChatEventKind
from app.models.conversation import MessageRole
from app.models.document_page import PredictionKind, PredictionValidationStatus
from app.models.dossier import (
    DossierStatus,
    ExecutionStepKind,
    ExecutionStepStatus,
    TextExtractionStatus,
)
from app.models.execution_log import ExecutionLogLevel
from app.models.feedback import FeedbackReasonCode, FeedbackValue


class BoundingBoxIn(BaseModel):
    x_min: float
    y_min: float
    x_max: float
    y_max: float


class BoundingBoxOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    x_min: float
    y_min: float
    x_max: float
    y_max: float


class DocumentPageSummaryOut(BaseModel):
    """Référence légère à une page, utilisée dans les schémas qui pointent
    vers un ensemble de pages (prédiction, source de message) - la page
    complète (avec ses prédictions) est déjà accessible via DossierOut."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    page_number: int


class PredictionValidationIn(BaseModel):
    status: PredictionValidationStatus
    corrected_value: str | None = None
    bounding_box: BoundingBoxIn | None = None


class PredictionValidationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    validator_user_id: str
    status: PredictionValidationStatus
    corrected_value: str | None
    bounding_box: BoundingBoxOut | None
    created_at: datetime


class DocumentPredictionSummaryOut(BaseModel):
    """Vue nichée dans DocumentPageOut.predictions : pas de `pages` ici (on
    est déjà sous une page) - la liste complète des pages d'une entité qui
    s'étend sur plusieurs d'entre elles n'est disponible que sur la
    prédiction elle-même (DocumentPredictionOut, endpoints dédiés)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: PredictionKind
    name: str
    value: str
    confidence: float | None
    # Présent seulement si la définition existe encore (voir le commentaire
    # sur DocumentPrediction.label_definition_id/entity_definition_id).
    label_definition_id: uuid.UUID | None
    entity_definition_id: uuid.UUID | None
    # Une classification n'a qu'un élément ; une entité peut n'être
    # localisée que par plusieurs zones, potentiellement sur d'autres pages.
    bounding_boxes: list[BoundingBoxOut]
    validations: list[PredictionValidationOut]


class DocumentPredictionOut(DocumentPredictionSummaryOut):
    # Une classification n'a qu'un élément ; une entité peut s'étendre sur
    # plusieurs pages.
    pages: list[DocumentPageSummaryOut]


class DocumentPageIn(BaseModel):
    page_number: int
    width: int | None = None
    height: int | None = None
    content: str | None = None
    # Clé S3 de la capture de la page, déjà uploadée par le worker (voir
    # storage.put_object) au moment de cet appel - jamais renvoyée telle
    # quelle par l'API, uniquement via GET .../pages/{id}/screenshot.
    screenshot_key: str | None = None


class DocumentPredictionIn(BaseModel):
    kind: PredictionKind
    name: str
    value: str
    confidence: float | None = None
    label_definition_id: uuid.UUID | None = None
    entity_definition_id: uuid.UUID | None = None
    # Pages/bbox additionnelles au-delà de la page de l'URL (POST
    # .../pages/{page_id}/predictions) : toujours incluse dans le résultat,
    # inutile de la répéter ici. Les bbox doivent déjà exister (voir POST
    # .../pages/{page_id}/bounding-boxes).
    page_ids: list[uuid.UUID] = []
    bounding_box_ids: list[uuid.UUID] = []


class MessageSourceIn(BaseModel):
    dossier_document_id: uuid.UUID | None = None
    execution_step_id: uuid.UUID | None = None
    excerpt: str | None = None
    # Du plus large au plus précis : le document ci-dessus suffit à minima,
    # mais la réponse peut citer un ensemble de pages ou, plus précisément,
    # un ensemble de bbox (déjà créées) sur ces pages.
    page_ids: list[uuid.UUID] = []
    bounding_box_ids: list[uuid.UUID] = []


class InternalMessageIn(BaseModel):
    content: str
    sources: list[MessageSourceIn] = []


class DocumentPageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    page_number: int
    width: int | None
    height: int | None
    content: str | None
    has_screenshot: bool
    bounding_boxes: list[BoundingBoxOut]
    predictions: list[DocumentPredictionSummaryOut]


class DossierDocumentIn(BaseModel):
    name: str
    size: int
    s3_key: str
    mimetype: str


class DossierDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    size: int
    s3_key: str
    mimetype: str
    label: str | None
    text_extraction_status: TextExtractionStatus
    text_extraction_error: str | None
    pages: list[DocumentPageOut]


class DossierDocumentLabelIn(BaseModel):
    label: str | None


class TextExtractionStatusIn(BaseModel):
    status: TextExtractionStatus
    error: str | None = None


class MessageSourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dossier_document_id: uuid.UUID | None
    execution_step_id: uuid.UUID | None
    excerpt: str | None
    pages: list[DocumentPageSummaryOut]
    bounding_boxes: list[BoundingBoxOut]


class MessageIn(BaseModel):
    content: str


class ConversationModelUpdate(BaseModel):
    # Identifiant de modèle tel que renvoyé par GET /models ; None = pas de
    # préférence, le hub par défaut sera utilisé.
    model: str | None


class FeedbackIn(BaseModel):
    value: FeedbackValue
    # Uniquement pertinent pour un pouce bas - jamais requis, un pouce haut
    # simple n'a aucune raison.
    reasons: list[FeedbackReasonCode] = []
    comment: str | None = None


class FeedbackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    message_id: uuid.UUID
    value: FeedbackValue
    reasons: list[FeedbackReasonCode]
    comment: str | None
    created_at: datetime


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: MessageRole
    content: str
    created_at: datetime
    sources: list[MessageSourceOut]
    feedback: FeedbackOut | None


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dossier_id: uuid.UUID
    user_id: str
    created_at: datetime
    model: str | None
    messages: list[MessageOut]


class ChatEventOut(BaseModel):
    """Événement d'exécution du chat (streaming). Déposé par le worker
    pendant l'exécution du graphe LangGraph, consommé par le frontend
    via SSE pour afficher la progression en temps réel."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    kind: ChatEventKind
    data: dict
    created_at: datetime


class ChatEventIn(BaseModel):
    """Payload pour déposer un événement de chat (worker → backend)."""

    kind: ChatEventKind
    data: dict = {}


class ConversationSummaryOut(BaseModel):
    """Vue légère pour la liste "mes conversations" de la sidebar (façon
    ChatGPT) : pas la liste complète des messages, juste de quoi afficher
    une entrée et y naviguer."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dossier_id: uuid.UUID
    dossier_name: str
    last_message_preview: str | None
    last_activity_at: datetime


class ExecutionLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    level: ExecutionLogLevel
    message: str
    created_at: datetime


class ExecutionStepOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: ExecutionStepKind
    label: str
    status: ExecutionStepStatus
    started_at: datetime
    ended_at: datetime | None
    output: str | None
    logs: list[ExecutionLogOut]


class ExecutionStepCompleteIn(BaseModel):
    status: ExecutionStepStatus
    output: str | None = None


class ExecutionLogIn(BaseModel):
    level: ExecutionLogLevel = ExecutionLogLevel.INFO
    message: str


class DossierCreate(BaseModel):
    name: str
    analyse_id: uuid.UUID


# --- Schémas internes (worker agent_execution) ---
# Ces schémas exposent les clés S3 (screenshot_key) et les définitions
# d'analyse (labels/entités/prompts) dont le worker a besoin pour
# télécharger les captures et exécuter la classification/extraction.
# Ils ne sont jamais renvoyés par l'API publique (seulement par
# /api/internal/*), pour ne pas fuiter les clés S3 côté frontend.


class InternalDocumentPageOut(BaseModel):
    """Page avec sa clé S3 de capture et ses prédictions (labels + entités)
    - réservé à l'API interne. Les prédictions sont nécessaires pour que
    l'agent LangGraph puisse consulter les classifications et entités déjà
    déposées par les tâches de classification/extraction."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    page_number: int
    content: str | None
    screenshot_key: str | None
    predictions: list[DocumentPredictionSummaryOut] = []


class InternalDossierDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    s3_key: str
    mimetype: str
    text_extraction_status: TextExtractionStatus
    pages: list[InternalDocumentPageOut]


class InternalExecutionStepOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: ExecutionStepKind
    label: str
    status: ExecutionStepStatus
    # Synthèse produite par l'agent (si output=True et étape terminée).
    # Nécessaire au chat pour injecter les synthèses existantes dans le
    # contexte de la conversation.
    output: str | None = None


class InternalMessageOut(BaseModel):
    """Message de conversation pour le worker (chat). Inclut le rôle et le
    contenu, sans les sources (le worker n'en a pas besoin pour construire
    son contexte - il génère les siennes)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: MessageRole
    content: str
    created_at: datetime


class InternalConversationOut(BaseModel):
    """Conversation complète pour le worker : messages (historique du chat)
    + modèle LLM préféré. Le worker en a besoin pour construire le contexte
    du graphe LangGraph de chat."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dossier_id: uuid.UUID
    model: str | None
    messages: list[InternalMessageOut]


class InternalDossierOut(BaseModel):
    """Dossier complet pour le worker : documents, pages (avec clés S3),
    étapes d'exécution. Pas de prédictions ici - le worker en dépose, il
    n'a pas besoin de les lire."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    analyse_id: uuid.UUID
    status: DossierStatus
    execution_steps: list[InternalExecutionStepOut]
    documents: list[InternalDossierDocumentOut]


class InternalLabelDefinitionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    definition: str


class InternalEntityDefinitionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    definition: str
    type: str


class InternalClassificationOut(BaseModel):
    prompt: str
    labels: list[InternalLabelDefinitionOut]


class InternalExtractionOut(BaseModel):
    prompt: str
    entities: list[InternalEntityDefinitionOut]


class InternalAgentOut(BaseModel):
    """Définition d'un agent pour le worker : prompt, outils, output, modèle.
    L'agent LangGraph utilise ces informations pour configurer son graphe."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    prompt: str
    tools: list[str]
    output: bool
    model: str | None


class InternalAnalyseOut(BaseModel):
    """Définitions de l'analyse (labels, entités, prompts, agents) pour le
    worker. Les agents sont gérés par la tâche LangGraph qui les exécute
    un par un après la classification et l'extraction."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    classification: InternalClassificationOut
    extraction: InternalExtractionOut
    agents: list[InternalAgentOut] = []


class DossierOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    analyse_id: uuid.UUID
    analyse_version: str
    created_at: datetime
    status: DossierStatus
    started_at: datetime | None
    ended_at: datetime | None
    execution_steps: list[ExecutionStepOut]
    documents: list[DossierDocumentOut]
